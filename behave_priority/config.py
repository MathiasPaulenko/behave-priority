"""Immutable configuration for priority execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriorityConfig:
    """Immutable configuration for priority execution.

    All configuration is programmatic — no CLI flags.
    """

    order: bool = False
    reverse: bool = False
    priority_tag: str | None = None
    stop_after_failures: int | None = None
    stop_on_critical: bool = False
    critical_tag: str = "critical"
    default_priority: int = 999
    report: bool = False
