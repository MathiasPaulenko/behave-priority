"""Immutable configuration for priority execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReportFormat = Literal["text", "json", "csv"]

_VALID_FORMATS: frozenset[str] = frozenset({"text", "json", "csv"})


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
        report_format: Output format for the report (``"text"``, ``"json"``, or ``"csv"``).
        parallel_coord: Enable cross-process fail-fast coordination via
            ``BEHAVE_PRIORITY_COORD_DIR`` env var. When True and the env
            var is set, workers share failure state via a file-based
            coordinator.

    Raises:
        ValueError: If ``stop_after_failures`` is not a positive integer
            (or None), if ``critical_tag`` or ``priority_tag`` is an empty
            string, if ``default_priority`` is negative, or if
            ``report_format`` is not one of ``"text"``, ``"json"``, ``"csv"``.
    """

    order: bool = False
    reverse: bool = False
    priority_tag: str | None = None
    stop_after_failures: int | None = None
    stop_on_critical: bool = False
    critical_tag: str = "critical"
    default_priority: int = 999
    report: bool = False
    report_format: ReportFormat = "text"
    parallel_coord: bool = False

    def __post_init__(self) -> None:
        """Validate configuration fields after initialization."""
        if self.stop_after_failures is not None and self.stop_after_failures <= 0:
            raise ValueError(
                f"stop_after_failures must be a positive integer or None, "
                f"got {self.stop_after_failures}"
            )
        if not self.critical_tag:
            raise ValueError("critical_tag must not be empty")
        if self.priority_tag is not None and not self.priority_tag:
            raise ValueError("priority_tag must not be empty if provided")
        if self.default_priority < 0:
            raise ValueError(
                f"default_priority must be non-negative, got {self.default_priority}"
            )
        if self.report_format not in _VALID_FORMATS:
            raise ValueError(
                f"report_format must be one of 'text', 'json', 'csv', "
                f"got {self.report_format!r}"
            )
