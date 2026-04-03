"""
Common tools shared across all workspace agents.
Re-exports from base_agent for convenience.
"""
from workspace.base_agent import (
    save_agent_report,
    send_department_message,
    save_department_report,
)

__all__ = [
    "save_agent_report",
    "send_department_message",
    "save_department_report",
]
