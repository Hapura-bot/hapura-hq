"""
vertex_config_client.py — Hapura Vertex Config Hub SDK
Copy file này vào backend/ của mỗi project consumer.

Dùng:
    from vertex_config_client import vertex_config

    # Trong startup:
    vertex_config.bootstrap("my-project-id")

    # Thay os.getenv:
    base_url = vertex_config.get("OPENAI_BASE_URL", default="https://vertex-key.com/api/v1")
    model    = vertex_config.get("MY_MODEL", default="omega/claude-haiku-4-5-20251001")
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger("vertex_config_client")

_POLL_INTERVAL = 60          # seconds
_CACHE_FILE_SUFFIX = ".vertex_config_cache.json"


class _VertexConfigClient:
    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._revision: int = 0
        self._project_id: Optional[str] = None
        self._hub_url: Optional[str] = None
        self._token: Optional[str] = None
        self._lock = threading.RLock()
        self._poll_thread: Optional[threading.Thread] = None
        self._bootstrapped = False

    # ── Public API ──────────────────────────────────────────────────────────

    def bootstrap(
        self,
        project_id: Optional[str] = None,
        hub_url: Optional[str] = None,
        token: Optional[str] = None,
        poll_interval: int = _POLL_INTERVAL,
    ) -> None:
        """
        Fetch config from hub on startup and start background polling.
        Falls back gracefully to os.getenv() if hub is unreachable.

        Reads from env vars if parameters not provided:
          VERTEX_CONFIG_PROJECT_ID, VERTEX_CONFIG_HUB_URL, VERTEX_CONFIG_TOKEN
        """
        self._project_id = project_id or os.getenv("VERTEX_CONFIG_PROJECT_ID", "")
        self._hub_url = (hub_url or os.getenv("VERTEX_CONFIG_HUB_URL", "")).rstrip("/")
        self._token = token or os.getenv("VERTEX_CONFIG_TOKEN", "")

        if not self._hub_url or not self._project_id or not self._token:
            logger.warning(
                "[vertex_config] Hub not configured — falling back to os.getenv(). "
                "Set VERTEX_CONFIG_HUB_URL, VERTEX_CONFIG_PROJECT_ID, VERTEX_CONFIG_TOKEN."
            )
            self._bootstrapped = True
            return

        # Initial fetch (synchronous so startup has config ready)
        self._fetch()
        self._bootstrapped = True

        # Start background polling thread
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            args=(poll_interval,),
            daemon=True,
            name="vertex-config-poll",
        )
        self._poll_thread.start()
        logger.info(
            "[vertex_config] Bootstrap done — project=%s rev=%s polling every %ss",
            self._project_id, self._revision, poll_interval,
        )

    def get(self, key: str, default: Any = None) -> str:
        """
        Return config value by env var key.
        Priority: hub cache → os.getenv → default.
        """
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        return os.getenv(key) or (default if default is not None else "")

    def reload(self) -> bool:
        """Force re-fetch from hub. Called by /admin/reload-vertex-config."""
        if not self._hub_url:
            return False
        return self._fetch()

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def is_connected(self) -> bool:
        return bool(self._hub_url and self._revision > 0)

    # ── Internal ────────────────────────────────────────────────────────────

    def _fetch(self) -> bool:
        """Fetch fresh config from hub. Returns True on success."""
        if not self._hub_url or not self._project_id or not self._token:
            return False
        url = f"{self._hub_url}/vertex-config/client/{self._project_id}"
        try:
            resp = httpx.get(
                url,
                headers={"X-Hapura-Token": self._token},
                timeout=8.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                new_config: dict[str, str] = data.get("config", {})
                new_rev: int = data.get("revision", 0)
                with self._lock:
                    self._cache = new_config
                    self._revision = new_rev
                logger.debug(
                    "[vertex_config] Refreshed rev=%s keys=%s",
                    new_rev, list(new_config.keys()),
                )
                self._write_cache(new_config, new_rev)
                return True
            else:
                logger.warning(
                    "[vertex_config] Hub returned %s — keeping cached config",
                    resp.status_code,
                )
                return False
        except Exception as exc:
            logger.warning("[vertex_config] Fetch failed: %s — keeping cached config", exc)
            self._try_load_cache()
            return False

    def _poll_loop(self, interval: int) -> None:
        while True:
            time.sleep(interval)
            self._fetch()

    # ── Disk cache (last-known-good fallback) ────────────────────────────────

    def _cache_path(self) -> str:
        pid = self._project_id or "default"
        return os.path.join(os.path.dirname(__file__), f"{pid}{_CACHE_FILE_SUFFIX}")

    def _write_cache(self, config: dict, rev: int) -> None:
        try:
            import json
            with open(self._cache_path(), "w", encoding="utf-8") as f:
                json.dump({"revision": rev, "config": config}, f)
        except Exception:
            pass  # Non-critical

    def _try_load_cache(self) -> None:
        """Load from disk cache if in-memory cache is empty (startup without hub)."""
        with self._lock:
            if self._cache:
                return
        try:
            import json
            with open(self._cache_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self._cache = data.get("config", {})
                self._revision = data.get("revision", 0)
            logger.info("[vertex_config] Loaded from disk cache rev=%s", self._revision)
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────
vertex_config = _VertexConfigClient()
