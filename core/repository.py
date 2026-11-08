"""Async repository for calendar-hermes (parameterized SQL only)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from .models import Calendar, Event

__all__ = ["Repository"]


def _row_calendar(row: Sequence[Any], agents: Optional[List[str]] = None) -> Calendar:
    return Calendar(
        id=str(row[0]),
        name=row[1],
        description=row[2] or "",
        created_at=row[3],
        updated_at=row[4],
        agents=agents or [],
    )


def _row_event(row: Sequence[Any]) -> Event:
    return Event(
        id=str(row[0]),
        calendar_id=str(row[1]),
        title=row[2],
        description=row[3] or "",
        location=row[4] or "",
        start_at=row[5],
        end_at=row[6],
        timezone=row[7] or "UTC",
        all_day=bool(row[8]),
        rrule=row[9],
        created_at=row[10],
        updated_at=row[11],
    )


class Repository:
    def __init__(self, db: Any) -> None:
        self._db = db

    async def _conn(self):
        return await self._db.connection()

    # -- calendars ---------------------------------------------------------

    async def list_calendars(self) -> List[Calendar]:
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT c.id, c.name, c.description, c.created_at, c.updated_at,
                           COALESCE(array_agg(ca.agent_name) FILTER (WHERE ca.agent_name IS NOT NULL), '{}')
                    FROM calendar.calendars c
                    LEFT JOIN calendar.calendar_agents ca ON ca.calendar_id = c.id
                    GROUP BY c.id
                    ORDER BY c.created_at ASC
                    """
                )
                rows = await cur.fetchall()
        return [_row_calendar(r[:5], list(r[5] or [])) for r in rows]

    async def get_calendar(self, calendar_id: str) -> Optional[Calendar]:
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT c.id, c.name, c.description, c.created_at, c.updated_at,
                           COALESCE(array_agg(ca.agent_name) FILTER (WHERE ca.agent_name IS NOT NULL), '{}')
                    FROM calendar.calendars c
                    LEFT JOIN calendar.calendar_agents ca ON ca.calendar_id = c.id
                    WHERE c.id = %s::uuid
                    GROUP BY c.id
                    """,
                    (calendar_id,),
                )
                row = await cur.fetchone()
        if not row:
            return None
        return _row_calendar(row[:5], list(row[5] or []))

    async def create_calendar(self, name: str, description: str = "") -> Calendar:
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO calendar.calendars (name, description)
                    VALUES (%s, %s)
                    RETURNING id, name, description, created_at, updated_at
                    """,
                    (name, description),
                )
                row = await cur.fetchone()
            await conn.commit()
        return _row_calendar(row, [])

    async def delete_calendar(self, calendar_id: str) -> bool:
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM calendar.calendars WHERE id = %s::uuid RETURNING id",
                    (calendar_id,),
                )
                row = await cur.fetchone()
            await conn.commit()
        return row is not None

    # -- events ------------------------------------------------------------

    _EVENT_COLS = (
        "id, calendar_id, title, description, location, start_at, end_at, "
        "timezone, all_day, rrule, created_at, updated_at"
    )

    async def get_event(self, event_id: str) -> Optional[Event]:
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT {self._EVENT_COLS} FROM calendar.events WHERE id = %s::uuid",
                    (event_id,),
                )
                row = await cur.fetchone()
        return _row_event(row) if row else None

    async def list_events_in_range(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        include_recurring: bool = True,
    ) -> List[Event]:
        # Fetch non-recurring in range OR recurring events that started before window end.
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                if include_recurring:
                    await cur.execute(
                        f"""
                        SELECT {self._EVENT_COLS} FROM calendar.events
                        WHERE calendar_id = %s::uuid
                          AND (
                            (rrule IS NULL AND start_at < %s AND end_at > %s)
                            OR (rrule IS NOT NULL AND start_at < %s)
                          )
                        ORDER BY start_at ASC
                        """,
                        (calendar_id, end, start, end),
                    )
                else:
                    await cur.execute(
                        f"""
                        SELECT {self._EVENT_COLS} FROM calendar.events
                        WHERE calendar_id = %s::uuid AND rrule IS NULL
                          AND start_at < %s AND end_at > %s
                        ORDER BY start_at ASC
                        """,
                        (calendar_id, end, start),
                    )
                rows = await cur.fetchall()
        return [_row_event(r) for r in rows]

    async def list_recurring_events(self, calendar_ids: List[str]) -> List[Event]:
        if not calendar_ids:
            return []
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    SELECT {self._EVENT_COLS} FROM calendar.events
                    WHERE calendar_id = ANY(%s::uuid[]) AND rrule IS NOT NULL
                    ORDER BY start_at ASC
                    """,
                    (calendar_ids,),
                )
                rows = await cur.fetchall()
        return [_row_event(r) for r in rows]

    async def create_event(
        self,
        calendar_id: str,
        title: str,
        start_at: datetime,
        end_at: datetime,
        description: str = "",
        location: str = "",
        timezone: str = "UTC",
        all_day: bool = False,
        rrule: Optional[str] = None,
    ) -> Event:
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    INSERT INTO calendar.events
                        (calendar_id, title, description, location, start_at, end_at, timezone, all_day, rrule)
                    VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING {self._EVENT_COLS}
                    """,
                    (
                        calendar_id,
                        title,
                        description,
                        location,
                        start_at,
                        end_at,
                        timezone,
                        all_day,
                        rrule,
                    ),
                )
                row = await cur.fetchone()
            await conn.commit()
        return _row_event(row)

    async def update_event(
        self, event_id: str, fields: Dict[str, Any]
    ) -> Optional[Event]:
        allowed = {
            "title",
            "description",
            "location",
            "start_at",
            "end_at",
            "timezone",
            "all_day",
            "rrule",
            "calendar_id",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return await self.get_event(event_id)
        sets = []
        params: List[Any] = []
        for key, value in updates.items():
            if key == "calendar_id":
                sets.append(f"{key} = %s::uuid")
            else:
                sets.append(f"{key} = %s")
            params.append(value)
        sets.append("updated_at = now()")
        params.append(event_id)
        sql = f"UPDATE calendar.events SET {', '.join(sets)} WHERE id = %s::uuid RETURNING {self._EVENT_COLS}"
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, tuple(params))
                row = await cur.fetchone()
            await conn.commit()
        return _row_event(row) if row else None

    async def delete_event(self, event_id: str) -> bool:
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM calendar.events WHERE id = %s::uuid RETURNING id",
                    (event_id,),
                )
                row = await cur.fetchone()
            await conn.commit()
        return row is not None

    async def search_events(
        self,
        query: str,
        start: datetime,
        end: datetime,
        calendar_id: Optional[str] = None,
    ) -> List[Event]:
        q = f"%{query}%"
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                if calendar_id:
                    await cur.execute(
                        f"""
                        SELECT {self._EVENT_COLS} FROM calendar.events
                        WHERE calendar_id = %s::uuid
                          AND start_at < %s AND end_at > %s
                          AND (title ILIKE %s OR description ILIKE %s OR location ILIKE %s)
                        ORDER BY start_at ASC
                        """,
                        (calendar_id, end, start, q, q, q),
                    )
                else:
                    await cur.execute(
                        f"""
                        SELECT {self._EVENT_COLS} FROM calendar.events
                        WHERE start_at < %s AND end_at > %s
                          AND (title ILIKE %s OR description ILIKE %s OR location ILIKE %s)
                        ORDER BY start_at ASC
                        """,
                        (end, start, q, q, q),
                    )
                rows = await cur.fetchall()
        return [_row_event(r) for r in rows]

    # -- exceptions --------------------------------------------------------

    async def add_exception(
        self,
        event_id: str,
        occurrence_start: datetime,
        action: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = overrides or {}
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO calendar.event_exceptions (event_id, occurrence_start, action, overrides)
                    VALUES (%s::uuid, %s, %s, %s::jsonb)
                    ON CONFLICT (event_id, occurrence_start)
                    DO UPDATE SET action = EXCLUDED.action, overrides = EXCLUDED.overrides, updated_at = now()
                    RETURNING id, event_id, occurrence_start, action, overrides, created_at, updated_at
                    """,
                    (event_id, occurrence_start, action, json.dumps(payload)),
                )
                row = await cur.fetchone()
            await conn.commit()
        return {
            "id": str(row[0]),
            "event_id": str(row[1]),
            "occurrence_start": row[2].isoformat() if row[2] else None,
            "action": row[3],
            "overrides": row[4] or {},
            "created_at": row[5].isoformat() if row[5] else None,
            "updated_at": row[6].isoformat() if row[6] else None,
        }

    async def list_exceptions(self, event_ids: List[str]) -> List[Dict[str, Any]]:
        if not event_ids:
            return []
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, event_id, occurrence_start, action, overrides, created_at, updated_at
                    FROM calendar.event_exceptions
                    WHERE event_id = ANY(%s::uuid[])
                    """,
                    (event_ids,),
                )
                rows = await cur.fetchall()
        return [
            {
                "id": str(r[0]),
                "event_id": str(r[1]),
                "occurrence_start": r[2],
                "action": r[3],
                "overrides": r[4] or {},
                "created_at": r[5],
                "updated_at": r[6],
            }
            for r in rows
        ]

    # -- agents ------------------------------------------------------------

    async def assign_agent(self, calendar_id: str, agent_name: str) -> bool:
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO calendar.calendar_agents (calendar_id, agent_name)
                    VALUES (%s::uuid, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING calendar_id
                    """,
                    (calendar_id, agent_name),
                )
                row = await cur.fetchone()
            await conn.commit()
        return row is not None or True  # idempotent

    async def unassign_agent(self, calendar_id: str, agent_name: str) -> bool:
        async with await self._conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    DELETE FROM calendar.calendar_agents
                    WHERE calendar_id = %s::uuid AND agent_name = %s
                    RETURNING calendar_id
                    """,
                    (calendar_id, agent_name),
                )
                row = await cur.fetchone()
            await conn.commit()
        return row is not None
