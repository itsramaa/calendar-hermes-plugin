"""RFC 5545 RRULE expansion. Pure function; importable without psycopg."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union
from zoneinfo import ZoneInfo

__all__ = ["expand_rrule", "parse_dt"]

_DEFAULT_WINDOW_DAYS = 60


def parse_dt(value: Union[str, datetime]) -> datetime:
    """Parse an ISO 8601 string (or pass a datetime through). Always tz-aware."""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _resolve_tz(tz: Optional[Union[str, ZoneInfo]]) -> ZoneInfo:
    if tz is None:
        return ZoneInfo("UTC")
    if isinstance(tz, ZoneInfo):
        return tz
    try:
        return ZoneInfo(str(tz))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Unknown timezone: {tz!r}") from exc


def expand_rrule(
    rrule_str: str,
    dtstart: datetime,
    tz: Optional[Union[str, ZoneInfo]],
    window_start: datetime,
    window_end: datetime,
) -> List[datetime]:
    """Expand an RRULE into occurrence start datetimes within the window.

    Returns occurrence STARTS. Raises ValueError on a malformed RRULE or if
    window_end is not after window_start.
    """
    if not rrule_str or not str(rrule_str).strip():
        raise ValueError("rrule_str must be a non-empty RRULE string")

    from dateutil.rrule import rrulestr

    tzinfo = _resolve_tz(tz)
    start = parse_dt(dtstart)
    w_start = parse_dt(window_start)
    w_end = parse_dt(window_end)

    if w_end <= w_start:
        raise ValueError("window_end must be after window_start")

    dtstart_local = start.astimezone(tzinfo)

    try:
        rule = rrulestr(rrule_str, dtstart=dtstart_local)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Malformed RRULE {rrule_str!r}: {exc}") from exc

    occurrences: List[datetime] = []
    # Expand in local tz then normalize to UTC for comparison/storage.
    cursor = rule.after(
        w_start.astimezone(tzinfo) - timedelta(microseconds=1), inc=True
    )
    guard = 0
    while cursor is not None and cursor < w_end.astimezone(tzinfo):
        occurrences.append(cursor.astimezone(timezone.utc))
        try:
            cursor = rule.after(cursor, inc=False)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Malformed RRULE {rrule_str!r}: {exc}") from exc
        guard += 1
        if guard > 100000:
            raise ValueError("RRULE expansion exceeded safety limit")
    return occurrences


def default_window(
    dtstart: datetime, days: int = _DEFAULT_WINDOW_DAYS
) -> tuple[datetime, datetime]:
    start = parse_dt(dtstart)
    return start, start + timedelta(days=max(1, days))
