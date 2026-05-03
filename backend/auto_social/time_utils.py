"""Datetime helpers — Asia/Ho_Chi_Minh is the canonical schedule timezone."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ICT = ZoneInfo("Asia/Ho_Chi_Minh")
SHEET_TIME_FMT = "%d/%m/%Y %H:%M"


def parse_schedule_time(value: str) -> datetime:
    """Parse 'DD/MM/YYYY HH:MM' as Asia/Ho_Chi_Minh local time."""
    dt = datetime.strptime(value.strip(), SHEET_TIME_FMT)
    return dt.replace(tzinfo=ICT)


def format_schedule_time(dt: datetime) -> str:
    """Format an aware datetime to 'DD/MM/YYYY HH:MM' in ICT."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ICT)
    return dt.astimezone(ICT).strftime(SHEET_TIME_FMT)


def now_ict() -> datetime:
    return datetime.now(ICT)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    """Aware datetime → ISO 8601 in ICT."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ICT).isoformat()


def to_iso_utc(dt: datetime) -> str:
    """Aware datetime → ISO 8601 UTC for Firestore storage."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso_utc(value: str) -> datetime:
    """Parse ISO 8601 string (with Z or +offset) to aware UTC datetime."""
    s = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
