"""
WorkspaceConfig — Per-product configuration for the AI Workplace.
Stored in Firestore `command_workspace_config` collection.
"""
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class WorkspaceConfig(BaseModel):
    product_id: str                                # "clippack"
    product_name: str                              # "ClipPack"
    platform: str                                  # "android" | "web" | "desktop"
    enabled_departments: list[str] = []            # ["executive", "growth", ...]
    enabled_agents: dict[str, list[str]] = {}      # {"growth": ["aso_analyst", ...]}
    data_sources: dict[str, dict] = {}             # {"playstore": {"package_name": "..."}}
    schedule_overrides: dict[str, str] = {}        # {"aso_analyst": "0 8 * * 1"}
    llm_overrides: dict[str, str] = {}             # {"director": "aws/claude-opus-4-6"}


class DepartmentMeta(BaseModel):
    id: str
    name: str
    name_vi: str
    description: str
    icon: str                                      # lucide icon name
    color: str                                     # tailwind neon color key
    agent_ids: list[str] = []
    lead_agent_id: Optional[str] = None
    health_score: int = 0                          # 0-100
    last_summary_at: Optional[str] = None


class AgentMessage(BaseModel):
    id: Optional[str] = None
    from_agent_id: str
    from_department: str
    to_department: str
    message_type: str                              # "finding" | "alert" | "recommendation" | "data"
    payload: dict = {}
    priority: str = "medium"                       # "high" | "medium" | "low"
    created_at: Optional[str] = None
    acknowledged: bool = False


class DepartmentReport(BaseModel):
    id: Optional[str] = None
    department_id: str
    period: str                                    # "2026-W14" or "2026-04"
    report_markdown: str = ""
    summary: str = ""
    key_metrics: dict = {}
    recommendations: list[str] = []
    generated_at: Optional[str] = None
    agent_run_ids: list[str] = []


class Directive(BaseModel):
    id: Optional[str] = None
    period: str                                    # "2026-W14"
    directive_type: str = "weekly"                 # "weekly" | "emergency"
    directive_markdown: str = ""
    priorities: list[str] = []
    department_actions: dict[str, list[str]] = {}  # dept_id -> action list
    generated_at: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    status: str = "draft"                          # "draft" | "approved" | "active" | "archived"
