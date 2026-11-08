"""Register Calendar Hermes tools with the Hermes plugin context."""

from __future__ import annotations

import logging
from typing import Any

from .handlers import (
    handle_calendar_add_exception,
    handle_calendar_assign_agent,
    handle_calendar_check_availability,
    handle_calendar_create_calendar,
    handle_calendar_create_event,
    handle_calendar_delete_calendar,
    handle_calendar_delete_event,
    handle_calendar_get_event,
    handle_calendar_list_calendars,
    handle_calendar_list_events,
    handle_calendar_search_events,
    handle_calendar_update_event,
)
from .schemas import (
    CALENDAR_ADD_EXCEPTION_SCHEMA,
    CALENDAR_ASSIGN_AGENT_SCHEMA,
    CALENDAR_CHECK_AVAILABILITY_SCHEMA,
    CALENDAR_CREATE_CALENDAR_SCHEMA,
    CALENDAR_CREATE_EVENT_SCHEMA,
    CALENDAR_DELETE_CALENDAR_SCHEMA,
    CALENDAR_DELETE_EVENT_SCHEMA,
    CALENDAR_GET_EVENT_SCHEMA,
    CALENDAR_LIST_CALENDARS_SCHEMA,
    CALENDAR_LIST_EVENTS_SCHEMA,
    CALENDAR_SEARCH_EVENTS_SCHEMA,
    CALENDAR_UPDATE_EVENT_SCHEMA,
)

__all__ = ["register_tools"]

logger = logging.getLogger(__name__)

_TOOLS = [
    (
        "calendar_list_calendars",
        CALENDAR_LIST_CALENDARS_SCHEMA,
        handle_calendar_list_calendars,
        "List all calendars.",
    ),
    (
        "calendar_create_calendar",
        CALENDAR_CREATE_CALENDAR_SCHEMA,
        handle_calendar_create_calendar,
        "Create a calendar.",
    ),
    (
        "calendar_delete_calendar",
        CALENDAR_DELETE_CALENDAR_SCHEMA,
        handle_calendar_delete_calendar,
        "Delete a calendar.",
    ),
    (
        "calendar_list_events",
        CALENDAR_LIST_EVENTS_SCHEMA,
        handle_calendar_list_events,
        "List events in a time window (recurrences expanded).",
    ),
    (
        "calendar_get_event",
        CALENDAR_GET_EVENT_SCHEMA,
        handle_calendar_get_event,
        "Fetch one event by ID.",
    ),
    (
        "calendar_create_event",
        CALENDAR_CREATE_EVENT_SCHEMA,
        handle_calendar_create_event,
        "Create an event (with optional RRULE).",
    ),
    (
        "calendar_update_event",
        CALENDAR_UPDATE_EVENT_SCHEMA,
        handle_calendar_update_event,
        "Update event fields.",
    ),
    (
        "calendar_delete_event",
        CALENDAR_DELETE_EVENT_SCHEMA,
        handle_calendar_delete_event,
        "Delete an event.",
    ),
    (
        "calendar_search_events",
        CALENDAR_SEARCH_EVENTS_SCHEMA,
        handle_calendar_search_events,
        "Full-text search on title/description/location.",
    ),
    (
        "calendar_check_availability",
        CALENDAR_CHECK_AVAILABILITY_SCHEMA,
        handle_calendar_check_availability,
        "Find free slots of N minutes.",
    ),
    (
        "calendar_add_exception",
        CALENDAR_ADD_EXCEPTION_SCHEMA,
        handle_calendar_add_exception,
        "Override a recurrence occurrence.",
    ),
    (
        "calendar_assign_agent",
        CALENDAR_ASSIGN_AGENT_SCHEMA,
        handle_calendar_assign_agent,
        "Assign an agent to a calendar.",
    ),
]


def register_tools(ctx: Any) -> None:
    for name, schema, handler, description in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="calendar-hermes",
            schema=schema,
            handler=handler,
            description=description,
            requires_env=["CALENDAR_PLUGIN_DSN"],
            is_async=True,
        )
    logger.debug("calendar-hermes: registered %d tools", len(_TOOLS))
