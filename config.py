"""Calendar Hermes configuration.

Reads settings from the environment. No secrets are emitted to logs,
error text, or tool responses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

__all__ = [
    "CalendarConfig",
    "DEFAULT_RECURRENCE_WINDOW_DAYS",
    "DEFAULT_AGENT_PROFILES_DIR",
]

DEFAULT_RECURRENCE_WINDOW_DAYS = 60
DEFAULT_AGENT_PROFILES_DIR = "../profiles"


@dataclass(frozen=True)
class CalendarConfig:
    dsn: str
    recurrence_window_days: int
    agent_profiles_dir: str

    @classmethod
    def from_env(cls) -> "CalendarConfig":
        dsn = os.environ.get("CALENDAR_PLUGIN_DSN", "").strip()
        if not dsn:
            fallback_name = "HONCHO_DATABASE_DSN"
            dsn = os.environ.get(fallback_name, "").strip()
        try:
            window = int(
                os.environ.get(
                    "CALENDAR_PLUGIN_RECURRENCE_WINDOW_DAYS",
                    DEFAULT_RECURRENCE_WINDOW_DAYS,
                )
            )
        except (TypeError, ValueError):
            window = DEFAULT_RECURRENCE_WINDOW_DAYS
        profiles_dir = os.environ.get(
            "CALENDAR_PLUGIN_AGENT_PROFILES_DIR", DEFAULT_AGENT_PROFILES_DIR
        )
        return cls(
            dsn=dsn,
            recurrence_window_days=max(1, window),
            agent_profiles_dir=profiles_dir,
        )

    @property
    def has_dsn(self) -> bool:
        return bool(self.dsn)

    def missing_dsn_message(self) -> str:
        return (
            "CALENDAR_PLUGIN_DSN is not set. Add it to your environment "
            "(e.g. data/.env). Fallback env var HONCHO_DATABASE_DSN is also "
            "checked when CALENDAR_PLUGIN_DSN is empty."
        )

    def resolved_agent_profiles_dir(self, plugin_dir: Optional[Path] = None) -> Path:
        path = Path(self.agent_profiles_dir)
        if not path.is_absolute() and plugin_dir is not None:
            path = (plugin_dir / path).resolve()
        return path
