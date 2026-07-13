"""Immutable configuration for priority execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriorityConfig:
    """Immutable configuration for priority execution.

    All configuration is programmatic — no CLI flags.

    Attributes:
        order: Sort scenarios by priority (highest first).
        reverse: Reverse sort order (lowest priority first).
        priority_tag: Tag name to run first (e.g. ``"smoke"``).
        stop_after_failures: Stop after N failed scenarios, or None to disable.
        stop_on_critical: Stop if any critical scenario fails.
        critical_tag: Tag name that marks a scenario as critical.
        default_priority: Priority for scenarios without a priority tag.
        report: Print execution report after run.
    """

    order: bool = False
    reverse: bool = False
    priority_tag: str | None = None
    stop_after_failures: int | None = None
    stop_on_critical: bool = False
    critical_tag: str = "critical"
    default_priority: int = 999
    report: bool = False
