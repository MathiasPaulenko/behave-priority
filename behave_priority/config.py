"""Immutable configuration for priority execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReportFormat = Literal["text", "json", "csv"]

_VALID_FORMATS: frozenset[str] = frozenset({"text", "json", "csv"})


def _clean_tag(tag: str) -> str:
    """Return the tag without surrounding whitespace or ``@`` prefix."""
    return tag.strip().removeprefix("@").strip()


@dataclass(frozen=True, slots=True)
class PriorityConfig:
    """Immutable configuration for priority execution.

    All configuration is programmatic — no CLI flags.

    Attributes:
        order: Sort scenarios by priority (highest first).
        reverse: Reverse sort order (lowest priority first).
        priority_tag: Tag name to run first (e.g. ``"smoke"``).
        stop_after_failures: Stop after N failed or errored scenarios,
            or None to disable.
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
            (or None), if ``critical_tag`` or ``priority_tag`` is not a
            string that normalizes to a non-empty tag name, if
            ``default_priority`` is not a non-negative integer, if any
            flag field (``order``, ``reverse``, ``stop_on_critical``,
            ``report``, ``parallel_coord``) is not a bool, or if
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
        if self.stop_after_failures is not None and (
            not isinstance(self.stop_after_failures, int)
            or isinstance(self.stop_after_failures, bool)
            or self.stop_after_failures <= 0
        ):
            raise ValueError(
                f"stop_after_failures must be a positive integer or None, "
                f"got {self.stop_after_failures!r}"
            )
        if (
            not isinstance(self.default_priority, int)
            or isinstance(self.default_priority, bool)
            or self.default_priority < 0
        ):
            raise ValueError(
                f"default_priority must be a non-negative integer, got {self.default_priority!r}"
            )
        if not isinstance(self.critical_tag, str) or not _clean_tag(self.critical_tag):
            raise ValueError(
                f"critical_tag must be a non-empty tag name, got {self.critical_tag!r}"
            )
        if self.priority_tag is not None and (
            not isinstance(self.priority_tag, str) or not _clean_tag(self.priority_tag)
        ):
            raise ValueError(
                f"priority_tag must be a non-empty tag name if provided, got {self.priority_tag!r}"
            )
        for flag in (
            "order",
            "reverse",
            "stop_on_critical",
            "report",
            "parallel_coord",
        ):
            if not isinstance(getattr(self, flag), bool):
                raise ValueError(f"{flag} must be a bool, got {getattr(self, flag)!r}")
        if self.report_format not in _VALID_FORMATS:
            raise ValueError(
                f"report_format must be one of 'text', 'json', 'csv', got {self.report_format!r}"
            )
