from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─── Project Room ─────────────────────────────────────────────────────────────

class ProjectRoom(BaseModel):
    id: str                         # "clippack" | "trendkr" | "hapu-studio" | "douyin-vi-dubber"
    name: str
    tagline: str
    platform: str                   # "android" | "web"
    status: str                     # "deployed" | "dev" | "planned"
    tech_stack: list[str]
    cloud_run_service_id: str
    github_repo: str
    frontend_url: str
    color_accent: str
    port_backend: Optional[int] = None
    port_frontend: Optional[int] = None
    phase_current: int = 1
    phase_total: int = 4
    phase_label: str = ""


class ProjectRoomUpdate(BaseModel):
    status: Optional[str] = None
    phase_current: Optional[int] = None
    phase_label: Optional[str] = None
    tagline: Optional[str] = None


# ─── Metrics ──────────────────────────────────────────────────────────────────

class MetricEntry(BaseModel):
    id: Optional[str] = None
    project_id: str
    period: str                     # "2026-04"
    revenue_vnd: int = 0
    active_users: int = 0
    new_signups: int = 0
    recorded_at: Optional[str] = None
    recorded_by: Optional[str] = None


class MetricCreate(BaseModel):
    project_id: str
    period: str
    revenue_vnd: int = 0
    active_users: int = 0
    new_signups: int = 0


# ─── Tasks (Kanban) ───────────────────────────────────────────────────────────

class Task(BaseModel):
    id: Optional[str] = None
    project_id: str
    title: str
    description: str = ""
    status: str = "todo"            # "todo" | "in_progress" | "done"
    priority: str = "medium"        # "high" | "medium" | "low"
    tags: list[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: str = ""
    priority: str = "medium"
    tags: list[str] = []


class TaskStatusUpdate(BaseModel):
    status: str


# ─── GP Score ─────────────────────────────────────────────────────────────────

class GPScore(BaseModel):
    project_id: str
    gp_total: int
    gp_revenue: int
    gp_users: int
    gp_velocity: int
    gp_uptime: int
    investment_multiplier: float
    is_focus: bool = False
