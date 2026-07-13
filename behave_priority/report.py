"""Execution report collection and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from behave_priority.config import PriorityConfig


@dataclass(frozen=True, slots=True)
class ReportEntry:
    """Single scenario entry in the execution report."""

    index: int
    feature_name: str
    scenario_name: str
    priority: int
    status: str
    duration: float
    is_critical: bool


@dataclass(frozen=True, slots=True)
class ReportSummary:
    """Aggregate statistics from the report."""

    total: int
    passed: int
    failed: int
    skipped: int
    undefined: int
    critical_total: int
    critical_passed: int
    critical_failed: int
    total_duration: float
    skipped_duration: float

    @property
    def time_saved(self) -> float:
        """Alias for skipped_duration."""
        return self.skipped_duration

    @property
    def pass_rate(self) -> float:
        """Percentage of passed scenarios (excluding skipped)."""
        executed = self.total - self.skipped
        if executed == 0:
            return 0.0
        return (self.passed / executed) * 100


class PriorityReport:
    """Collects and renders execution order with priorities and timing."""

    def __init__(self, config: PriorityConfig) -> None:
        self._config = config
        self._entries: list[ReportEntry] = []

    def record(
        self,
        *,
        scenario_name: str,
        feature_name: str,
        priority: int,
        status: str,
        duration: float,
        is_critical: bool,
    ) -> None:
        """Record a scenario execution result."""
        entry = ReportEntry(
            index=len(self._entries) + 1,
            feature_name=feature_name,
            scenario_name=scenario_name,
            priority=priority,
            status=status,
            duration=duration,
            is_critical=is_critical,
        )
        self._entries.append(entry)

    def render(self) -> str:
        """Render the full report as a formatted string."""
        if not self._entries:
            return (
                "Priority Execution Report\n"
                "=========================\n\n"
                "No scenarios executed.\n"
            )

        lines: list[str] = []
        lines.append("Priority Execution Report")
        lines.append("=========================")
        lines.append("")

        header = (
            f"{'#':>3}  {'Priority':>8}  "
            f"{'Feature':<30}  {'Scenario':<40}  "
            f"{'Status':<8}  {'Duration':>8}"
        )
        lines.append(header)
        lines.append("-" * len(header))

        for entry in self._entries:
            feature = (
                entry.feature_name[:27] + "..."
                if len(entry.feature_name) > 30
                else entry.feature_name
            )
            scenario = (
                entry.scenario_name[:37] + "..."
                if len(entry.scenario_name) > 40
                else entry.scenario_name
            )
            lines.append(
                f"{entry.index:>3}  {entry.priority:>8}  "
                f"{feature:<30}  {scenario:<40}  "
                f"{entry.status:<8}  {entry.duration:>7.2f}s"
            )

        lines.append("")
        summary = self.summary()
        lines.append("Summary:")
        if summary.critical_total > 0:
            lines.append(
                f"  Critical: {summary.critical_passed}/{summary.critical_total} passed"
            )
        lines.append(
            f"  Total: {summary.passed} passed, {summary.failed} failed, "
            f"{summary.skipped} skipped"
        )
        if summary.skipped > 0:
            lines.append(
                f"  Time saved by fail-fast: {summary.skipped_duration:.2f}s "
                f"({summary.skipped} scenario(s) skipped)"
            )

        return "\n".join(lines) + "\n"

    def summary(self) -> ReportSummary:
        """Compute aggregate statistics."""
        total = len(self._entries)
        passed = sum(1 for e in self._entries if e.status == "passed")
        failed = sum(1 for e in self._entries if e.status == "failed")
        skipped = sum(1 for e in self._entries if e.status == "skipped")
        undefined = sum(1 for e in self._entries if e.status == "undefined")

        critical_entries = [e for e in self._entries if e.is_critical]
        critical_total = len(critical_entries)
        critical_passed = sum(1 for e in critical_entries if e.status == "passed")
        critical_failed = sum(1 for e in critical_entries if e.status == "failed")

        total_duration = sum(e.duration for e in self._entries)
        skipped_duration = sum(e.duration for e in self._entries if e.status == "skipped")

        return ReportSummary(
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            undefined=undefined,
            critical_total=critical_total,
            critical_passed=critical_passed,
            critical_failed=critical_failed,
            total_duration=total_duration,
            skipped_duration=skipped_duration,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dictionary."""
        summary = self.summary()
        return {
            "entries": [
                {
                    "index": e.index,
                    "feature_name": e.feature_name,
                    "scenario_name": e.scenario_name,
                    "priority": e.priority,
                    "status": e.status,
                    "duration": e.duration,
                    "is_critical": e.is_critical,
                }
                for e in self._entries
            ],
            "summary": {
                "total": summary.total,
                "passed": summary.passed,
                "failed": summary.failed,
                "skipped": summary.skipped,
                "undefined": summary.undefined,
                "critical_total": summary.critical_total,
                "critical_passed": summary.critical_passed,
                "critical_failed": summary.critical_failed,
                "total_duration": summary.total_duration,
                "skipped_duration": summary.skipped_duration,
            },
        }
