"""Calendar Hermes dashboard — backend API routes.

Mounted at /api/plugins/calendar-hermes/ by the dashboard plugin system.
DB connections are opened lazily on the first request. The plugin package
is located dynamically so this module can be exec'd standalone by the
dashboard server.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

_ISO = str


def _load() -> Any:
    """Import the calendar-hermes plugin package in whichever context it exists."""
    for name in ("hermes_plugins.calendar_hermes", "calendar_hermes"):
        try:
            mod = importlib.import_module(name)
            sys.modules.setdefault("calendar_hermes", mod)
            return mod
        except Exception:
            pass

    import importlib.util

    plugin_root = Path(__file__).resolve().parent.parent
    if str(plugin_root) not in sys.path:
        sys.path.insert(0, str(plugin_root))
    spec = importlib.util.spec_from_file_location(
        "calendar_hermes",
        plugin_root / "__init__.py",
        submodule_search_locations=[str(plugin_root)],
    )
    if spec is None or spec.loader is None:
        raise HTTPException(
            status_code=500, detail="calendar-hermes plugin not importable"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules["calendar_hermes"] = module
    spec.loader.exec_module(module)
    return module


_pkg = _load()


def _service() -> Any:
    config_module = importlib.import_module(f"{_pkg.__name__}.config")
    db_module = importlib.import_module(f"{_pkg.__name__}.db.connection")
    service_module = importlib.import_module(f"{_pkg.__name__}.core.service")
    repo_module = importlib.import_module(f"{_pkg.__name__}.core.repository")

    plugin_config = config_module.CalendarConfig.from_env()
    if not plugin_config.has_dsn:
        raise HTTPException(status_code=503, detail=plugin_config.missing_dsn_message())

    db = _DB()
    return service_module.CalendarService(repo_module.Repository(db), plugin_config)


class _DB:
    """Small async bridge so plugin_api works without a live pool at import time."""

    def __init__(self) -> None:
        self._db: Optional[Any] = None

    async def connection(self) -> Any:
        if self._db is None:
            db_module = importlib.import_module(f"{_pkg.__name__}.db.connection")
            config_module = importlib.import_module(f"{_pkg.__name__}.config")
            self._db = await db_module.get_database(
                config_module.CalendarConfig.from_env()
            )
        # Database.connection() returns the pool connection CM after open().
        return await self._db.connection()


class CreateCalendarBody(BaseModel):
    name: str
    description: str = ""


class CreateEventBody(BaseModel):
    title: str
    start_at: Optional[_ISO] = None
    end_at: Optional[_ISO] = None
    start: Optional[_ISO] = None  # frontend alias
    end: Optional[_ISO] = None  # frontend alias
    description: str = ""
    location: str = ""
    timezone: str = "UTC"
    all_day: bool = False
    rrule: Optional[str] = None


class UpdateEventBody(BaseModel):
    title: Optional[str] = None
    start_at: Optional[_ISO] = None
    end_at: Optional[_ISO] = None
    start: Optional[_ISO] = None  # frontend alias
    end: Optional[_ISO] = None  # frontend alias
    description: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    all_day: Optional[bool] = None
    rrule: Optional[str] = None
    calendar_id: Optional[str] = None


class AddExceptionBody(BaseModel):
    occurrence_start: _ISO
    action: str
    overrides: Optional[Dict[str, Any]] = None


class AssignAgentBody(BaseModel):
    agent_name: Optional[str] = None
    agent: Optional[str] = None  # frontend alias


def _wrap(func):
    async def inner(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise exc
            raise HTTPException(status_code=500, detail=str(exc))

    return inner


@router.post("/calendars/{calendar_id}/agents")
async def assign_agent(calendar_id: str, body: AssignAgentBody) -> Dict[str, Any]:
    service = _service()
    agent_name = body.agent_name or body.agent
    if not agent_name or not str(agent_name).strip():
        raise HTTPException(status_code=422, detail="agent_name/agent is required")
    await service.assign_agent(calendar_id, str(agent_name).strip())
    return {
        "assigned": True,
        "calendar_id": calendar_id,
        "agent_name": str(agent_name).strip(),
    }


@router.get("/calendars")
async def list_calendars() -> Dict[str, Any]:
    service = _service()
    calendars = await service.list_calendars()
    items = [c.to_dict() for c in calendars]
    return {"calendars": items, "data": items}


@router.post("/calendars")
async def create_calendar(body: CreateCalendarBody) -> Dict[str, Any]:
    service = _service()
    calendar = await service.create_calendar(body.name, body.description)
    return {"calendar": calendar.to_dict()}


@router.delete("/calendars/{calendar_id}")
async def delete_calendar(calendar_id: str) -> Dict[str, Any]:
    service = _service()
    deleted = await service.delete_calendar(calendar_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="calendar not found")
    return {"deleted": True, "calendar_id": calendar_id}


@router.get("/calendars/{calendar_id}/events")
async def list_calendar_events(
    calendar_id: str,
    start: _ISO = Query(...),
    end: _ISO = Query(...),
) -> Dict[str, Any]:
    service = _service()
    occurrences = await service.list_events(calendar_id, start, end)
    items = [o.to_dict() for o in occurrences]
    return {"occurrences": items, "data": items}


@router.post("/calendars/{calendar_id}/events")
async def create_event(calendar_id: str, body: CreateEventBody) -> Dict[str, Any]:
    service = _service()
    start_at = body.start_at or body.start
    end_at = body.end_at or body.end
    if not start_at or not end_at:
        raise HTTPException(
            status_code=422, detail="start_at/start and end_at/end are required"
        )
    event = await service.create_event(
        calendar_id=calendar_id,
        title=body.title,
        start_at=start_at,
        end_at=end_at,
        description=body.description,
        location=body.location,
        timezone_name=body.timezone,
        all_day=body.all_day,
        rrule=body.rrule,
    )
    return {"event": event.to_dict()}


@router.patch("/calendars/{calendar_id}/events/{event_id}")
async def update_event(
    calendar_id: str, event_id: str, body: UpdateEventBody
) -> Dict[str, Any]:
    del calendar_id
    service = _service()
    raw = body.model_dump()
    # Normalize frontend aliases before filtering None (so explicit nulls don't linger oddly).
    if raw.get("start") is not None and raw.get("start_at") is None:
        raw["start_at"] = raw["start"]
    if raw.get("end") is not None and raw.get("end_at") is None:
        raw["end_at"] = raw["end"]
    raw.pop("start", None)
    raw.pop("end", None)
    fields = {k: v for k, v in raw.items() if v is not None}
    event = await service.update_event(event_id, **fields)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return {"event": event.to_dict()}


@router.delete("/calendars/{calendar_id}/events/{event_id}")
async def delete_event(calendar_id: str, event_id: str) -> Dict[str, Any]:
    del calendar_id
    service = _service()
    deleted = await service.delete_event(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="event not found")
    return {"deleted": True, "event_id": event_id}


@router.post("/calendars/{calendar_id}/events/{event_id}/exceptions")
async def add_exception(
    calendar_id: str, event_id: str, body: AddExceptionBody
) -> Dict[str, Any]:
    del calendar_id
    service = _service()
    try:
        result = await service.add_exception(
            event_id, body.occurrence_start, body.action, body.overrides
        )
    except Exception as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail="event not found") from exc
        raise
    return {"exception": result}


@router.get("/free-busy")
async def free_busy(
    calendar_ids: List[str] = Query(...),
    start: _ISO = Query(...),
    end: _ISO = Query(...),
    duration_min: int = Query(default=60, ge=1),
) -> Dict[str, Any]:
    service = _service()
    slots = await service.find_free_slots(calendar_ids, start, end, duration_min)
    items = [s.to_dict() for s in slots]
    return {"slots": items, "data": items}
