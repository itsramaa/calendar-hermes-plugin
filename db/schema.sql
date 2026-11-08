-- calendar-hermes schema (PostgreSQL)
CREATE SCHEMA IF NOT EXISTS calendar;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS calendar.calendars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS calendar.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendar.calendars(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    all_day BOOLEAN NOT NULL DEFAULT FALSE,
    rrule TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT events_time_order CHECK (end_at > start_at)
);

CREATE INDEX IF NOT EXISTS idx_events_calendar_id ON calendar.events(calendar_id);
CREATE INDEX IF NOT EXISTS idx_events_start_at ON calendar.events(start_at);
CREATE INDEX IF NOT EXISTS idx_events_search ON calendar.events
    USING gin (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(location,'')));

CREATE TABLE IF NOT EXISTS calendar.event_exceptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES calendar.events(id) ON DELETE CASCADE,
    occurrence_start TIMESTAMPTZ NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('delete', 'reschedule', 'modify')),
    overrides JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT event_exceptions_unique UNIQUE (event_id, occurrence_start)
);

CREATE INDEX IF NOT EXISTS idx_event_exceptions_event_id ON calendar.event_exceptions(event_id);

CREATE TABLE IF NOT EXISTS calendar.calendar_agents (
    calendar_id UUID NOT NULL REFERENCES calendar.calendars(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (calendar_id, agent_name)
);

CREATE INDEX IF NOT EXISTS idx_calendar_agents_agent ON calendar.calendar_agents(agent_name);
