"""
BaseWorkspaceAgent — Standardized pattern for all workspace agents.
Wraps the existing PraisonAI Agent+Task+Agents pattern with:
- Automatic Firestore report saving
- Cross-department message sending
- Structured metadata output
"""
from __future__ import annotations
import os
import logging
from datetime import datetime
from typing import Callable
from praisonaiagents import Agent, Task, Agents
from praisonaiagents.tools import tool

logger = logging.getLogger(__name__)


def setup_llm(model_key: str = "llm_model") -> str:
    """Configure OpenAI env vars and return model name from config."""
    from config import get_settings
    import litellm
    s = get_settings()
    if s.openai_api_key:
        os.environ["OPENAI_API_KEY"] = s.openai_api_key
        os.environ["OPENAI_BASE_URL"] = s.openai_base_url

    # vertex-key.com proxy does not support streaming for Claude models.
    # Patch litellm.completion to force stream=False for all workspace agent calls.
    if not getattr(litellm, "_hapura_stream_patched", False):
        _orig = litellm.completion
        def _completion_no_stream(*args, **kwargs):
            kwargs["stream"] = False
            return _orig(*args, **kwargs)
        litellm.completion = _completion_no_stream
        litellm._hapura_stream_patched = True
    return getattr(s, model_key, s.llm_model)


def save_agent_report(
    agent_id: str,
    report: str,
    summary: str,
    metadata: dict | None = None,
    triggered_by: str = "workspace",
) -> str:
    """Save agent run report to Firestore. Returns document ID."""
    from firebase_admin import firestore
    db = firestore.client()
    now = datetime.utcnow().isoformat()
    ref = db.collection("command_agent_runs").document()
    ref.set({
        "agent_id": agent_id,
        "status": "done",
        "triggered_by": triggered_by,
        "started_at": now,
        "finished_at": now,
        "report_markdown": report[:10000],
        "summary": summary[:300],
        "metadata": metadata or {},
    })
    return ref.id


def send_department_message(
    from_agent_id: str,
    from_department: str,
    to_department: str,
    message_type: str,
    payload: dict,
    priority: str = "medium",
) -> str:
    """Send a cross-department message via Firestore. Returns doc ID."""
    from firebase_admin import firestore
    db = firestore.client()
    ref = db.collection("command_agent_messages").document()
    ref.set({
        "from_agent_id": from_agent_id,
        "from_department": from_department,
        "to_department": to_department,
        "message_type": message_type,
        "payload": payload,
        "priority": priority,
        "created_at": datetime.utcnow().isoformat(),
        "acknowledged": False,
    })
    return ref.id


def save_department_report(
    department_id: str,
    period: str,
    report_markdown: str,
    summary: str,
    key_metrics: dict | None = None,
    recommendations: list[str] | None = None,
    agent_run_ids: list[str] | None = None,
) -> str:
    """Save a department summary report. Returns doc ID."""
    from firebase_admin import firestore
    db = firestore.client()
    ref = db.collection("command_department_reports").document()
    ref.set({
        "department_id": department_id,
        "period": period,
        "report_markdown": report_markdown[:10000],
        "summary": summary[:300],
        "key_metrics": key_metrics or {},
        "recommendations": recommendations or [],
        "generated_at": datetime.utcnow().isoformat(),
        "agent_run_ids": agent_run_ids or [],
    })
    return ref.id


def run_workspace_agent(
    agent_id: str,
    name: str,
    role: str,
    goal: str,
    backstory: str,
    tools: list[Callable],
    task_description: str,
    expected_output: str,
    model_key: str = "llm_model",
    triggered_by: str = "workspace",
) -> dict:
    """Run a PraisonAI agent with the standard workspace pattern."""
    llm = setup_llm(model_key)

    agent = Agent(
        name=name,
        role=role,
        goal=goal,
        backstory=backstory,
        tools=tools,
        llm=llm,
    )

    task = Task(
        description=task_description,
        expected_output=expected_output,
        agent=agent,
    )

    pipeline = Agents(agents=[agent], tasks=[task])
    result = pipeline.start()

    return {"result": str(result), "agent_id": agent_id, "triggered_by": triggered_by}
