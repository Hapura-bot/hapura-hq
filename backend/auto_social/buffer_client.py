"""Buffer GraphQL API client.

Endpoint: https://api.buffer.com/graphql
Auth: Bearer <api_key>

Verified end-to-end on 2026-05-02 (Phase A live test).

Schema notes:
- Query.account, Query.channels(input: ChannelsInput!), Query.post(input: PostInput!)
- Mutation.createPost(input: CreatePostInput!) -> PostActionSuccess | MutationError | UnexpectedError
- Mutation.deletePost(input: DeletePostInput!) -> DeletePostSuccess | VoidMutationError
- Post.externalLink is the published TikTok URL (NOT serviceLink).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


class BufferError(Exception):
    pass


class BufferAuthError(BufferError):
    pass


class BufferRateLimitError(BufferError):
    pass


@dataclass
class BufferAccount:
    id: str
    email: str
    organization_id: str
    organization_name: str


@dataclass
class BufferChannel:
    id: str
    name: str
    service: str
    service_id: str
    timezone: str
    is_disconnected: bool
    external_link: str | None


@dataclass
class BufferPost:
    id: str
    status: str
    text: str | None
    due_at: datetime | None
    external_link: str | None


def _to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class BufferClient:
    """Sync GraphQL client. Thread-safe via httpx.Client."""

    def __init__(self, api_key: str | None = None, endpoint: str | None = None) -> None:
        s = get_settings()
        self._api_key = api_key or s.buffer_api_key
        self._endpoint = (endpoint or s.buffer_graphql_url).rstrip("/") + "/graphql"
        self._client_lock = threading.Lock()
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        with self._client_lock:
            if self._client is None:
                if not self._api_key:
                    raise BufferAuthError(
                        "BUFFER_API_KEY not configured. Set in env or pass api_key explicitly."
                    )
                self._client = httpx.Client(
                    base_url=self._endpoint,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )
            return self._client

    def close(self) -> None:
        with self._client_lock:
            if self._client is not None:
                self._client.close()
                self._client = None

    def _request(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        client = self._get_client()
        body: dict[str, Any] = {"query": query}
        if variables is not None:
            body["variables"] = variables
        r = client.post("", json=body)

        if r.status_code == 401:
            raise BufferAuthError("Invalid API key (HTTP 401)")
        if r.status_code == 429:
            raise BufferRateLimitError(f"Rate limit exceeded: {r.text[:200]}")
        if r.status_code >= 500:
            raise BufferError(f"Buffer server error {r.status_code}: {r.text[:200]}")

        try:
            payload = r.json()
        except Exception as e:
            raise BufferError(f"Invalid JSON response: {r.text[:200]}") from e

        if "errors" in payload:
            messages = "; ".join(e.get("message", "?") for e in payload["errors"])
            raise BufferError(f"GraphQL errors: {messages}")

        return payload.get("data", {})

    # ── Queries ───────────────────────────────────────────────────────────

    def get_account(self) -> BufferAccount:
        q = """query Account {
          account {
            id email
            currentOrganization { id name }
          }
        }"""
        data = self._request(q)
        a = data["account"]
        org = a["currentOrganization"]
        return BufferAccount(
            id=a["id"],
            email=a["email"],
            organization_id=org["id"],
            organization_name=org["name"],
        )

    def list_channels(self, organization_id: str) -> list[BufferChannel]:
        q = """query Channels($orgId: OrganizationId!) {
          channels(input: { organizationId: $orgId }) {
            id name service serviceId timezone isDisconnected externalLink
          }
        }"""
        data = self._request(q, {"orgId": organization_id})
        return [
            BufferChannel(
                id=c["id"],
                name=c["name"],
                service=c["service"],
                service_id=c.get("serviceId") or "",
                timezone=c.get("timezone") or "",
                is_disconnected=bool(c.get("isDisconnected")),
                external_link=c.get("externalLink"),
            )
            for c in data["channels"]
        ]

    def get_post(self, post_id: str) -> BufferPost | None:
        q = """query Post($input: PostInput!) {
          post(input: $input) {
            id status text dueAt externalLink
          }
        }"""
        try:
            data = self._request(q, {"input": {"id": post_id}})
        except BufferError as e:
            if "not found" in str(e).lower():
                return None
            raise
        p = data.get("post")
        if not p:
            return None
        return BufferPost(
            id=p["id"],
            status=p.get("status") or "",
            text=p.get("text"),
            due_at=_parse_dt(p.get("dueAt")),
            external_link=p.get("externalLink"),
        )

    # ── Mutations ─────────────────────────────────────────────────────────

    def create_scheduled_post(
        self,
        *,
        channel_id: str,
        text: str,
        due_at: datetime,
        video_url: str,
        thumbnail_url: str | None = None,
        video_title: str | None = None,
        save_to_draft: bool = False,
    ) -> BufferPost:
        m = """mutation CreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            __typename
            ... on PostActionSuccess { post { id status text dueAt externalLink } }
            ... on MutationError { message }
            ... on UnexpectedError { message }
          }
        }"""
        video_asset: dict[str, Any] = {"url": video_url}
        if thumbnail_url:
            video_asset["thumbnailUrl"] = thumbnail_url
        if video_title:
            video_asset["metadata"] = {"title": video_title}

        input_obj: dict[str, Any] = {
            "channelId": channel_id,
            "text": text,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": _to_utc_iso(due_at),
            "assets": {"videos": [video_asset]},
        }
        if save_to_draft:
            input_obj["saveToDraft"] = True

        data = self._request(m, {"input": input_obj})
        result = data["createPost"]
        typename = result.get("__typename", "")
        if typename != "PostActionSuccess":
            msg = result.get("message", "unknown error")
            raise BufferError(f"createPost {typename}: {msg}")

        p = result["post"]
        return BufferPost(
            id=p["id"],
            status=p.get("status") or "",
            text=p.get("text"),
            due_at=_parse_dt(p.get("dueAt")),
            external_link=p.get("externalLink"),
        )

    def delete_post(self, post_id: str) -> bool:
        m = """mutation DeletePost($input: DeletePostInput!) {
          deletePost(input: $input) {
            __typename
            ... on VoidMutationError { message }
          }
        }"""
        data = self._request(m, {"input": {"id": post_id}})
        result = data["deletePost"]
        typename = result.get("__typename", "")
        if typename != "DeletePostSuccess":
            msg = result.get("message", "unknown error")
            raise BufferError(f"deletePost {typename}: {msg}")
        return True
