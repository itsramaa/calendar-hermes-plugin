"""CalendarService: business logic shared by tools and the dashboard API."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..config import CalendarConfig
from .models import Agent, Calendar, Event, EventOccurrence, FreeSlot
from .repository import Repository
from .rrule_engine import expand_rrule, parse_dt

__all__ = ["CalendarService", "NotFoundError", "ValidationError"]

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised when a requested entity does not exist."""


class ValidationError(Exception):
    """Raised when input fails validation."""


class CalendarService:
    def __init__(
        self, repo: Repository, config: Optional[CalendarConfig] = None
    ) -> None:
        self._repo = repo
        self._config = config or CalendarConfig.from_env()

    # -- calendars ---------------------------------------------------------

    async def list_calendars(self, agent_name: Optional[str] = None) -> List[Calendar]:
        calendars = await self._repo.list_calendars()
        target_agent = agent_name or os.environ.get("HERMES_PROFILE") or os.environ.get("HERMES_PROFILE_ID")
        if target_agent and target_agent != "default":
            # Multi-profile scoping: show unassigned/shared calendars + calendars linked to this agent
            scoped = [c for c in calendars if not c.agents or target_agent in c.agents]
            return scoped if scoped else calendars
        return calendars

    async def create_calendar(self, name: str, description: str = "") -> Calendar:
        name = (name or "").strip()
        if not name:
            raise ValidationError("name must be a non-empty string")
        return await self._repo.create_calendar(name, description or "")

    async def delete_calendar(self, calendar_id: str) -> bool:
        return await self._repo.delete_calendar(calendar_id)

    async def get_calendar(self, calendar_id: str) -> Optional[Calendar]:
        return await self._repo.get_calendar(calendar_id)

    # -- events ------------------------------------------------------------

    async def get_event(self, event_id: str) -> Optional[Event]:
        return await self._repo.get_event(event_id)

    async def create_event(
        self,
        calendar_id: str,
        title: str,
        start_at: Union[str, datetime],
        end_at: Union[str, datetime],
        description: str = "",
        location: str = "",
        timezone_name: str = "UTC",
        all_day: bool = False,
        rrule: Optional[str] = None,
    ) -> Event:
        title = (title or "").strip()
        if not title:
            raise ValidationError("title must be a non-empty string")
        start = parse_dt(start_at)
        end = parse_dt(end_at)
        if end <= start:
            raise ValidationError("end_at must be after start_at")
        if rrule:
            self._validate_rrule(rrule, start, timezone_name)
        return await self._repo.create_event(
            calendar_id=calendar_id,
            title=title,
            start_at=start,
            end_at=end,
            description=description or "",
            location=location or "",
            timezone=timezone_name or "UTC",
            all_day=bool(all_day),
            rrule=rrule or None,
        )

    async def update_event(self, event_id: str, **fields: Any) -> Optional[Event]:
        clean: Dict[str, Any] = {}
        for key in (
            "title",
            "description",
            "location",
            "timezone",
            "all_day",
            "rrule",
            "calendar_id",
        ):
            if key in fields and fields[key] is not None:
                clean[key] = fields[key]
        for key in ("start_at", "end_at"):
            if key in fields and fields[key] is not None:
                clean[key] = parse_dt(fields[key])
        if "rrule" in clean and clean["rrule"]:
            start = clean.get("start_at")
            if start is None:
                existing = await self._repo.get_event(event_id)
                if existing is None:
                    return None
                start = existing.start_at
            self._validate_rrule(clean["rrule"], start, clean.get("timezone", "UTC"))
        updated = await self._repo.update_event(event_id, clean)
        return updated

    async def delete_event(self, event_id: str) -> bool:
        return await self._repo.delete_event(event_id)

    async def search_events(
        self,
        query: str,
        start: Union[str, datetime],
        end: Union[str, datetime],
        calendar_id: Optional[str] = None,
    ) -> List[Event]:
        query = (query or "").strip()
        if not query:
            raise ValidationError("query must be a non-empty string")
        return await self._repo.search_events(
            query, parse_dt(start), parse_dt(end), calendar_id
        )

    # -- occurrence expansion ---------------------------------------------

    async def list_events(
        self,
        calendar_id: str,
        start: Union[str, datetime],
        end: Union[str, datetime],
    ) -> List[EventOccurrence]:
        w_start = parse_dt(start)
        w_end = parse_dt(end)
        if w_end <= w_start:
            raise ValidationError("end must be after start")
        events = await self._repo.list_events_in_range(calendar_id, w_start, w_end)
        exceptions = await self._repo.list_exceptions([e.id for e in events if e.rrule])
        exc_by_event: Dict[str, Dict[datetime, Dict[str, Any]]] = {}
        for exc in exceptions:
            exc_by_event.setdefault(exc["event_id"], {})[
                parse_dt(exc["occurrence_start"])
            ] = exc

        occurrences: List[EventOccurrence] = []
        for event in events:
            if not event.rrule:
                occurrences.append(
                    self._occurrence(event, event.start_at, event.end_at)
                )
                continue
            duration = event.end_at - event.start_at
            try:
                starts = expand_rrule(
                    event.rrule, event.start_at, event.timezone, w_start, w_end
                )
            except ValueError as exc:
                logger.warning("calendar-hermes: skipping event %s: %s", event.id, exc)
                continue
            event_exc = exc_by_event.get(event.id, {})
            for occ_start in starts:
                occ_end = occ_start + duration
                exc = self._match_exception(event_exc, occ_start)
                if exc is not None:
                    if exc["action"] == "delete":
                        continue
                    overrides = exc.get("overrides") or {}
                    new_start = (
                        parse_dt(overrides["start_at"])
                        if overrides.get("start_at")
                        else occ_start
                    )
                    new_end = (
                        parse_dt(overrides["end_at"])
                        if overrides.get("end_at")
                        else new_start + duration
                    )
                    occurrences.append(
                        self._occurrence(
                            event,
                            new_start,
                            new_end,
                            occ_start=occ_start,
                            occ_end=occ_end,
                            overridden=True,
                        )
                    )
                    continue
                if occ_end <= w_start or occ_start >= w_end:
                    continue
                occurrences.append(self._occurrence(event, occ_start, occ_end))
        occurrences.sort(key=lambda o: o.start_at)
        return occurrences

    async def add_exception(
        self,
        event_id: str,
        occurrence_start: Union[str, datetime],
        action: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if action not in {"delete", "reschedule", "modify"}:
            raise ValidationError("action must be one of delete, reschedule, modify")
        event = await self._repo.get_event(event_id)
        if event is None:
            raise NotFoundError(f"event {event_id} not found")
        return await self._repo.add_exception(
            event_id, parse_dt(occurrence_start), action, overrides
        )

    # -- availability ------------------------------------------------------

    async def find_free_slots(
        self,
        calendar_ids: List[str],
        start: Union[str, datetime],
        end: Union[str, datetime],
        duration_min: int,
    ) -> List[FreeSlot]:
        w_start = parse_dt(start)
        w_end = parse_dt(end)
        if w_end <= w_start:
            raise ValidationError("end must be after start")
        if duration_min <= 0:
            raise ValidationError("duration_min must be positive")

        busy: List[tuple[datetime, datetime]] = []
        for calendar_id in calendar_ids:
            occurrences = await self.list_events(calendar_id, w_start, w_end)
            for occ in occurrences:
                busy.append((occ.start_at, occ.end_at))
        busy.sort(key=lambda t: t[0])

        merged: List[tuple[datetime, datetime]] = []
        for b_start, b_end in busy:
            if merged and b_start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b_end))
            else:
                merged.append((b_start, b_end))

        needed = timedelta(minutes=duration_min)
        slots: List[FreeSlot] = []
        cursor = w_start
        for b_start, b_end in merged:
            if b_start - cursor >= needed:
                slots.append(FreeSlot(start_at=cursor, end_at=b_start))
            cursor = max(cursor, b_end)
        if w_end - cursor >= needed:
            slots.append(FreeSlot(start_at=cursor, end_at=w_end))
        return slots

    # -- agents ------------------------------------------------------------

    async def list_agents(self) -> List[Agent]:
        names: List[str] = []
        profiles_dir = self._config.resolved_agent_profiles_dir(
            Path(__file__).resolve().parent.parent
        )
        if profiles_dir.is_dir():
            for child in sorted(profiles_dir.iterdir()):
                if child.is_dir():
                    names.append(child.name)
        if not names:
            raw = self._config.agent_profiles_dir
            names = [n.strip() for n in str(raw).split(",") if n.strip()]
        return [Agent(name=n) for n in names]

    async def assign_agent(self, calendar_id: str, agent_name: str) -> bool:
        if not (agent_name or "").strip():
            raise ValidationError("agent_name must be a non-empty string")
        return await self._repo.assign_agent(calendar_id, agent_name.strip())

    async def unassign_agent(self, calendar_id: str, agent_name: str) -> bool:
        return await self._repo.unassign_agent(calendar_id, agent_name.strip())

    # -- helpers -----------------------------------------------------------

    def _validate_rrule(self, rrule: str, start: datetime, tz: str) -> None:
        try:
            expand_rrule(rrule, start, tz, start, start + timedelta(days=1))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    @staticmethod
    def _occurrence(
        event: Event,
        start: datetime,
        end: datetime,
        occ_start: Optional[datetime] = None,
        occ_end: Optional[datetime] = None,
        overridden: bool = False,
    ) -> EventOccurrence:
        return EventOccurrence(
            event_id=event.id,
            calendar_id=event.calendar_id,
            title=event.title,
            start_at=start,
            end_at=end,
            occurrence_start=occ_start or start,
            occurrence_end=occ_end or end,
            overridden=overridden,
            description=event.description,
            location=event.location,
        )

    @staticmethod
    def _match_exception(
        event_exc: Dict[datetime, Dict[str, Any]], occ_start: datetime
    ) -> Optional[Dict[str, Any]]:
        target = occ_start.astimezone(timezone.utc)
        for key in (occ_start, target):
            if key in event_exc:
                return event_exc[key]
        for stored_start, exc in event_exc.items():
            if (
                abs((stored_start.astimezone(timezone.utc) - target).total_seconds())
                < 1
            ):
                return exc
        return None
