"""Dataclasses for calendar-hermes domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

__all__ = [
    "Calendar",
    "Event",
    "EventOccurrence",
    "FreeSlot",
    "Agent",
]


@dataclass
class Calendar:
    id: str
    name: str
    description: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    agents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "agents": list(self.agents),
        }


@dataclass
class Event:
    id: str
    calendar_id: str
    title: str
    start_at: datetime
    end_at: datetime
    description: str = ""
    location: str = ""
    timezone: str = "UTC"
    all_day: bool = False
    rrule: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        start = _iso(self.start_at)
        end = _iso(self.end_at)
        return {
            "id": self.id,
            "calendar_id": self.calendar_id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "start_at": start,
            "end_at": end,
            "start": start,  # dashboard frontend alias
            "end": end,  # dashboard frontend alias
            "timezone": self.timezone,
            "all_day": self.all_day,
            "rrule": self.rrule,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


@dataclass
class EventOccurrence:
    event_id: str
    calendar_id: str
    title: str
    start_at: datetime
    end_at: datetime
    occurrence_start: datetime
    occurrence_end: datetime
    overridden: bool = False
    description: str = ""
    location: str = ""

    def to_dict(self) -> Dict[str, Any]:
        start = _iso(self.start_at)
        end = _iso(self.end_at)
        return {
            "id": self.event_id,  # dashboard frontend alias
            "event_id": self.event_id,
            "calendar_id": self.calendar_id,
            "title": self.title,
            "start_at": start,
            "end_at": end,
            "start": start,  # dashboard frontend alias
            "end": end,  # dashboard frontend alias
            "occurrence_start": _iso(self.occurrence_start),
            "occurrence_end": _iso(self.occurrence_end),
            "overridden": self.overridden,
            "description": self.description,
            "location": self.location,
        }


@dataclass
class FreeSlot:
    start_at: datetime
    end_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        start = _iso(self.start_at)
        end = _iso(self.end_at)
        return {"start_at": start, "end_at": end, "start": start, "end": end}


@dataclass
class Agent:
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None
