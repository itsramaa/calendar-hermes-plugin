"""JSON Schemas for Calendar Hermes tools."""

from __future__ import annotations

__all__ = [
    "CALENDAR_LIST_CALENDARS_SCHEMA",
    "CALENDAR_CREATE_CALENDAR_SCHEMA",
    "CALENDAR_DELETE_CALENDAR_SCHEMA",
    "CALENDAR_LIST_EVENTS_SCHEMA",
    "CALENDAR_GET_EVENT_SCHEMA",
    "CALENDAR_CREATE_EVENT_SCHEMA",
    "CALENDAR_UPDATE_EVENT_SCHEMA",
    "CALENDAR_DELETE_EVENT_SCHEMA",
    "CALENDAR_SEARCH_EVENTS_SCHEMA",
    "CALENDAR_CHECK_AVAILABILITY_SCHEMA",
    "CALENDAR_ADD_EXCEPTION_SCHEMA",
    "CALENDAR_ASSIGN_AGENT_SCHEMA",
]

_ISO_DT = {"type": "string", "description": "ISO 8601 datetime (timezone recommended)."}

CALENDAR_LIST_CALENDARS_SCHEMA = {
    "description": "List all calendars with their assigned agents.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}

CALENDAR_CREATE_CALENDAR_SCHEMA = {
    "description": "Create a new calendar.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Calendar name."},
            "description": {"type": "string", "description": "Optional description."},
        },
        "required": ["name"],
        "additionalProperties": False,
    },
}

CALENDAR_DELETE_CALENDAR_SCHEMA = {
    "description": "Delete a calendar and its events.",
    "parameters": {
        "type": "object",
        "properties": {
            "calendar_id": {"type": "string", "description": "Calendar UUID."},
        },
        "required": ["calendar_id"],
        "additionalProperties": False,
    },
}

CALENDAR_LIST_EVENTS_SCHEMA = {
    "description": "List events in a time window with recurrences expanded.",
    "parameters": {
        "type": "object",
        "properties": {
            "calendar_id": {"type": "string", "description": "Calendar UUID."},
            "start": {**_ISO_DT, "description": "Window start (ISO 8601)."},
            "end": {**_ISO_DT, "description": "Window end (ISO 8601)."},
        },
        "required": ["calendar_id", "start", "end"],
        "additionalProperties": False,
    },
}

CALENDAR_GET_EVENT_SCHEMA = {
    "description": "Fetch one event by ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "Event UUID."},
        },
        "required": ["event_id"],
        "additionalProperties": False,
    },
}

CALENDAR_CREATE_EVENT_SCHEMA = {
    "description": (
        "Create an event. Provide rrule for recurrence (e.g. "
        "FREQ=WEEKLY;BYDAY=MO,WE;INTERVAL=2)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "calendar_id": {"type": "string", "description": "Calendar UUID."},
            "title": {"type": "string", "description": "Event title."},
            "start_at": {**_ISO_DT, "description": "Event start (ISO 8601)."},
            "end_at": {**_ISO_DT, "description": "Event end (ISO 8601)."},
            "description": {"type": "string", "description": "Optional description."},
            "location": {"type": "string", "description": "Optional location."},
            "timezone": {
                "type": "string",
                "description": "IANA timezone (default UTC).",
            },
            "all_day": {"type": "boolean", "description": "All-day flag."},
            "rrule": {
                "type": "string",
                "description": "RFC 5545 RRULE string (optional).",
            },
        },
        "required": ["calendar_id", "title", "start_at", "end_at"],
        "additionalProperties": False,
    },
}

CALENDAR_UPDATE_EVENT_SCHEMA = {
    "description": "Update event fields by ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "Event UUID."},
            "calendar_id": {"type": "string", "description": "Move to calendar UUID."},
            "title": {"type": "string"},
            "start_at": _ISO_DT,
            "end_at": _ISO_DT,
            "description": {"type": "string"},
            "location": {"type": "string"},
            "timezone": {"type": "string"},
            "all_day": {"type": "boolean"},
            "rrule": {"type": "string", "description": "New RRULE or empty to clear."},
        },
        "required": ["event_id"],
        "additionalProperties": False,
    },
}

CALENDAR_DELETE_EVENT_SCHEMA = {
    "description": "Delete an event.",
    "parameters": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "Event UUID."},
        },
        "required": ["event_id"],
        "additionalProperties": False,
    },
}

CALENDAR_SEARCH_EVENTS_SCHEMA = {
    "description": "Full-text search on event title, description, and location.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search text."},
            "start": {**_ISO_DT, "description": "Window start (ISO 8601)."},
            "end": {**_ISO_DT, "description": "Window end (ISO 8601)."},
            "calendar_id": {
                "type": "string",
                "description": "Optional calendar UUID filter.",
            },
        },
        "required": ["query", "start", "end"],
        "additionalProperties": False,
    },
}

CALENDAR_CHECK_AVAILABILITY_SCHEMA = {
    "description": "Find free slots of N minutes across calendars.",
    "parameters": {
        "type": "object",
        "properties": {
            "calendar_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Calendar UUIDs to check.",
            },
            "start": {**_ISO_DT, "description": "Window start (ISO 8601)."},
            "end": {**_ISO_DT, "description": "Window end (ISO 8601)."},
            "duration_min": {
                "type": "integer",
                "minimum": 1,
                "description": "Required slot length in minutes.",
            },
        },
        "required": ["calendar_ids", "start", "end", "duration_min"],
        "additionalProperties": False,
    },
}

CALENDAR_ADD_EXCEPTION_SCHEMA = {
    "description": "Override a recurrence occurrence (delete, reschedule, or modify).",
    "parameters": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "Event UUID."},
            "occurrence_start": {
                **_ISO_DT,
                "description": "Original occurrence start (ISO 8601).",
            },
            "action": {
                "type": "string",
                "enum": ["delete", "reschedule", "modify"],
                "description": "Exception action.",
            },
            "overrides": {
                "type": "object",
                "description": "Override fields (e.g. start_at, end_at, title).",
                "additionalProperties": True,
            },
        },
        "required": ["event_id", "occurrence_start", "action"],
        "additionalProperties": False,
    },
}

CALENDAR_ASSIGN_AGENT_SCHEMA = {
    "description": "Assign an agent to a calendar.",
    "parameters": {
        "type": "object",
        "properties": {
            "calendar_id": {"type": "string", "description": "Calendar UUID."},
            "agent_name": {"type": "string", "description": "Agent name."},
        },
        "required": ["calendar_id", "agent_name"],
        "additionalProperties": False,
    },
}
