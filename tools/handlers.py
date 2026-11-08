"""Tool handlers for Calendar Hermes. All handlers are async and return JSON strings."""

from __future__ import annotations

import logging
from typing import Any, Optional

from tools.registry import tool_error, tool_result

from ..config import CalendarConfig
from ..core.repository import Repository
from ..core.service import CalendarService, NotFoundError, ValidationError
from ..db.connection import get_database

__all__ = [
    "handle_calendar_list_calendars",
    "handle_calendar_create_calendar",
    "handle_calendar_delete_calendar",
    "handle_calendar_list_events",
    "handle_calendar_get_event",
    "handle_calendar_create_event",
    "handle_calendar_update_event",
    "handle_calendar_delete_event",
    "handle_calendar_search_events",
    "handle_calendar_check_availability",
    "handle_calendar_add_exception",
    "handle_calendar_assign_agent",
]

logger = logging.getLogger(__name__)


async def _service() -> CalendarService:
    config = CalendarConfig.from_env()
    if not config.has_dsn:
        raise RuntimeError(config.missing_dsn_message())
    db = await get_database(config)
    return CalendarService(Repository(db), config)


def _err(exc: Exception) -> str:
    if isinstance(exc, NotFoundError):
        return tool_error(str(exc), code="not_found")
    if isinstance(exc, ValidationError):
        return tool_error(str(exc), code="validation_error")
    if isinstance(exc, RuntimeError):
        return tool_error(str(exc), code="config_error")
    logger.exception("calendar-hermes tool error")
    return tool_error(str(exc))


def _need(args: dict, key: str) -> Optional[str]:
    value = args.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if value is not None and not isinstance(value, str):
        return str(value)
    return None


async def handle_calendar_list_calendars(args: dict, **kwargs: Any) -> str:
    del args, kwargs
    try:
        service = await _service()
        calendars = await service.list_calendars()
        return tool_result({"calendars": [c.to_dict() for c in calendars]})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_create_calendar(args: dict, **kwargs: Any) -> str:
    del kwargs
    name = _need(args, "name")
    if not name:
        return tool_error("name must be a non-empty string")
    try:
        service = await _service()
        calendar = await service.create_calendar(
            name=name, description=args.get("description") or ""
        )
        return tool_result({"calendar": calendar.to_dict()})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_delete_calendar(args: dict, **kwargs: Any) -> str:
    del kwargs
    calendar_id = _need(args, "calendar_id")
    if not calendar_id:
        return tool_error("calendar_id must be a non-empty string")
    try:
        service = await _service()
        deleted = await service.delete_calendar(calendar_id)
        if not deleted:
            return tool_error(f"calendar {calendar_id} not found", code="not_found")
        return tool_result({"deleted": True, "calendar_id": calendar_id})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_list_events(args: dict, **kwargs: Any) -> str:
    del kwargs
    calendar_id = _need(args, "calendar_id")
    start = _need(args, "start")
    end = _need(args, "end")
    if not calendar_id or not start or not end:
        return tool_error("calendar_id, start, and end are required")
    try:
        service = await _service()
        occurrences = await service.list_events(calendar_id, start, end)
        return tool_result({"occurrences": [o.to_dict() for o in occurrences]})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_get_event(args: dict, **kwargs: Any) -> str:
    del kwargs
    event_id = _need(args, "event_id")
    if not event_id:
        return tool_error("event_id must be a non-empty string")
    try:
        service = await _service()
        event = await service.get_event(event_id)
        if event is None:
            return tool_error(f"event {event_id} not found", code="not_found")
        return tool_result({"event": event.to_dict()})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_create_event(args: dict, **kwargs: Any) -> str:
    del kwargs
    calendar_id = _need(args, "calendar_id")
    title = _need(args, "title")
    start_at = _need(args, "start_at")
    end_at = _need(args, "end_at")
    if not calendar_id or not title or not start_at or not end_at:
        return tool_error("calendar_id, title, start_at, and end_at are required")
    try:
        service = await _service()
        event = await service.create_event(
            calendar_id=calendar_id,
            title=title,
            start_at=start_at,
            end_at=end_at,
            description=args.get("description") or "",
            location=args.get("location") or "",
            timezone_name=args.get("timezone") or "UTC",
            all_day=bool(args.get("all_day")),
            rrule=args.get("rrule") or None,
        )
        return tool_result({"event": event.to_dict()})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_update_event(args: dict, **kwargs: Any) -> str:
    del kwargs
    event_id = _need(args, "event_id")
    if not event_id:
        return tool_error("event_id must be a non-empty string")
    fields = {
        k: args[k]
        for k in (
            "calendar_id",
            "title",
            "description",
            "location",
            "start_at",
            "end_at",
            "timezone",
            "all_day",
            "rrule",
        )
        if k in args
    }
    try:
        service = await _service()
        event = await service.update_event(event_id, **fields)
        if event is None:
            return tool_error(f"event {event_id} not found", code="not_found")
        return tool_result({"event": event.to_dict()})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_delete_event(args: dict, **kwargs: Any) -> str:
    del kwargs
    event_id = _need(args, "event_id")
    if not event_id:
        return tool_error("event_id must be a non-empty string")
    try:
        service = await _service()
        deleted = await service.delete_event(event_id)
        if not deleted:
            return tool_error(f"event {event_id} not found", code="not_found")
        return tool_result({"deleted": True, "event_id": event_id})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_search_events(args: dict, **kwargs: Any) -> str:
    del kwargs
    query = _need(args, "query")
    start = _need(args, "start")
    end = _need(args, "end")
    if not query or not start or not end:
        return tool_error("query, start, and end are required")
    try:
        service = await _service()
        events = await service.search_events(
            query=query,
            start=start,
            end=end,
            calendar_id=_need(args, "calendar_id"),
        )
        return tool_result({"events": [e.to_dict() for e in events]})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_check_availability(args: dict, **kwargs: Any) -> str:
    del kwargs
    calendar_ids = args.get("calendar_ids")
    start = _need(args, "start")
    end = _need(args, "end")
    duration_min = args.get("duration_min")
    if not isinstance(calendar_ids, list) or not calendar_ids or not start or not end:
        return tool_error("calendar_ids, start, and end are required")
    try:
        duration = int(duration_min)
    except (TypeError, ValueError):
        return tool_error("duration_min must be a positive integer")
    try:
        service = await _service()
        slots = await service.find_free_slots(
            [str(c) for c in calendar_ids], start, end, duration
        )
        return tool_result({"slots": [s.to_dict() for s in slots]})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_add_exception(args: dict, **kwargs: Any) -> str:
    del kwargs
    event_id = _need(args, "event_id")
    occurrence_start = _need(args, "occurrence_start")
    action = _need(args, "action")
    if not event_id or not occurrence_start or not action:
        return tool_error("event_id, occurrence_start, and action are required")
    overrides = args.get("overrides")
    if overrides is not None and not isinstance(overrides, dict):
        return tool_error("overrides must be an object")
    try:
        service = await _service()
        result = await service.add_exception(
            event_id=event_id,
            occurrence_start=occurrence_start,
            action=action,
            overrides=overrides,
        )
        return tool_result({"exception": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


async def handle_calendar_assign_agent(args: dict, **kwargs: Any) -> str:
    del kwargs
    calendar_id = _need(args, "calendar_id")
    agent_name = _need(args, "agent_name")
    if not calendar_id or not agent_name:
        return tool_error("calendar_id and agent_name are required")
    try:
        service = await _service()
        await service.assign_agent(calendar_id, agent_name)
        return tool_result(
            {"assigned": True, "calendar_id": calendar_id, "agent_name": agent_name}
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
