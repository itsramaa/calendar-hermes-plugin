"""Lazy async PostgreSQL connection pool for calendar-hermes.

# deps:
#   psycopg[binary]>=3.1
#   psycopg-pool>=3.1
#   python-dateutil>=2.8
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from ..config import CalendarConfig

__all__ = ["Database", "get_database"]

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class Database:
    """Owns an AsyncConnectionPool and schema initialization."""

    def __init__(self, config: CalendarConfig) -> None:
        self._config = config
        self._pool = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def open(self) -> None:
        if self._pool is not None:
            return
        async with self._lock:
            if self._pool is not None:
                return
            if not self._config.has_dsn:
                raise RuntimeError(self._config.missing_dsn_message())
            try:
                from psycopg_pool import AsyncConnectionPool
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "psycopg-pool is required for calendar-hermes. "
                    "Install with: pip install 'psycopg[binary]' psycopg-pool"
                ) from exc
            self._pool = AsyncConnectionPool(
                conninfo=self._config.dsn,
                min_size=1,
                max_size=5,
                open=False,
            )
            await self._pool.open()
            await self._ensure_schema()

    async def close(self) -> None:
        async with self._lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
                self._initialized = False

    async def _ensure_schema(self) -> None:
        if self._initialized or self._pool is None:
            return
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(schema_sql)
            await conn.commit()
        self._initialized = True
        logger.debug("calendar-hermes: schema ensured")

    async def connection(self):
        """Return an async context manager yielding a connection."""
        await self.open()
        assert self._pool is not None
        return self._pool.connection()


_db_singleton: Optional[Database] = None
_db_lock = asyncio.Lock()


async def get_database(config: Optional[CalendarConfig] = None) -> Database:
    global _db_singleton
    if _db_singleton is not None:
        return _db_singleton
    async with _db_lock:
        if _db_singleton is not None:
            return _db_singleton
        cfg = config or CalendarConfig.from_env()
        _db_singleton = Database(cfg)
        return _db_singleton
