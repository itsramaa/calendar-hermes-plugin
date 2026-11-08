"""Calendar Hermes plugin entry point."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["register"]


def register(ctx: Any) -> None:
    """Register Calendar Hermes tools."""
    from .tools import register_tools

    register_tools(ctx)
    logger.debug("calendar-hermes: registered tools")
