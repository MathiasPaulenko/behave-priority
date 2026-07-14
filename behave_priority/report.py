"""Execution report collection and rendering."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from behave_priority.config import PriorityConfig


@dataclass(frozen=True, slots=True)
class ReportEntry:
    """Single scenario entry in the execution report.

    Attributes:
        index: 1-based position in execution order.
        feature_name: Name or filename of the parent feature.
        scenario_name: Display name of the scenario.
        priority: Resolved priority value.
        status: Execution status (``"passed"``, ``"failed"``, etc.).
        duration: Execution time in seconds.
        is_critical: Whether the scenario has the critical tag.
    """

    index: int
    feature_name: str
    scenario_name: str
    priority: int
    status: str
    duration: float
    is_critical: bool


@dataclass(frozen=True, slots=True)
class ReportSummary:
    """Aggregate statistics from the report.

    Attributes:
        total: Total number of recorded scenarios.
        passed: Number of passed scenarios.
        failed: Number of failed scenarios.
        skipped: Number of skipped scenarios.
        undefined: Number of undefined scenarios.
        untested: Number of scenarios with a status not matching any known category.
        critical_total: Total number of critical scenarios.
        critical_passed: Number of passed critical scenarios.
        critical_failed: Number of failed critical scenarios.
        critical_skipped: Number of skipped critical scenarios.
        total_duration: Sum of all scenario durations in seconds.
        skipped_duration: Sum of skipped scenario durations in seconds.
        time_saved: Estimated time saved by skipping scenarios, using
            priority-bucketed averages of executed scenario durations.
    """

    total: int
    passed: int
    failed: int
    skipped: int
    undefined: int = 0
    untested: int = 0
    critical_total: int = 0
    critical_passed: int = 0
    critical_failed: int = 0
    critical_skipped: int = 0
    total_duration: float = 0.0
    skipped_duration: float = 0.0
    time_saved: float = 0.0

    @property
    def pass_rate(self) -> float:
        """Percentage of passed scenarios excluding skipped and undefined.

        Returns:
            Pass rate as a percentage (0.0 to 100.0).
        """
        executed = self.total - self.skipped - self.undefined
        if executed <= 0:
            return 0.0
        return (self.passed / executed) * 100


class PriorityReport:
    """Collects and renders execution order with priorities and timing."""

    def __init__(self, config: PriorityConfig) -> None:
        """Initialize the report collector.

        Args:
            config: Configuration that controls report behavior.
        """
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
        """Record a scenario execution result.

        Args:
            scenario_name: Display name of the scenario.
            feature_name: Name or filename of the parent feature.
            priority: Resolved priority value.
            status: Execution status (``"passed"``, ``"failed"``, etc.).
            duration: Execution time in seconds.
            is_critical: Whether the scenario has the critical tag.
        """
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
        """Render the full report as a formatted string.

        Column widths for Feature and Scenario names are computed
        dynamically from the actual content, with a maximum of 40
        characters to avoid excessive width. Names longer than the
        computed width are truncated with ``...``.

        Returns:
            A human-readable report with a table of entries and summary.
        """
        if not self._entries:
            return (
                "Priority Execution Report\n"
                "=========================\n\n"
                "No scenarios executed.\n"
            )

        feature_width = min(
            max(max(len(e.feature_name) for e in self._entries), len("Feature")),
            40,
        )
        scenario_width = min(
            max(max(len(e.scenario_name) for e in self._entries), len("Scenario")),
            40,
        )
        status_width = max(
            max(len(e.status) for e in self._entries), len("Status"),
        )
        duration_width = max(
            max(len(f"{e.duration:.2f}s") for e in self._entries),
            len("Duration"),
        )

        lines: list[str] = []
        lines.append("Priority Execution Report")
        lines.append("=========================")
        lines.append("")

        header = (
            f"{'#':>3}  {'Priority':>8}  "
            f"{'Feature':<{feature_width}}  {'Scenario':<{scenario_width}}  "
            f"{'Status':<{status_width}}  {'Duration':>{duration_width}}"
        )
        lines.append(header)
        lines.append("-" * len(header))

        for entry in self._entries:
            feature = self._truncate(entry.feature_name, feature_width)
            scenario = self._truncate(entry.scenario_name, scenario_width)
            lines.append(
                f"{entry.index:>3}  {entry.priority:>8}  "
                f"{feature:<{feature_width}}  {scenario:<{scenario_width}}  "
                f"{entry.status:<{status_width}}  {entry.duration:>{duration_width - 1}.2f}s"
            )

        lines.append("")
        summary = self.summary()
        lines.append("Summary:")
        if summary.critical_total > 0:
            crit_line = (
                f"  Critical: {summary.critical_passed}/{summary.critical_total} passed"
            )
            if summary.critical_skipped > 0:
                crit_line += f", {summary.critical_skipped} skipped"
            lines.append(crit_line)
        total_line = (
            f"  Total: {summary.passed} passed, {summary.failed} failed, "
            f"{summary.skipped} skipped"
        )
        if summary.undefined > 0:
            total_line += f", {summary.undefined} undefined"
        lines.append(total_line)
        if summary.untested > 0:
            lines.append(f"  Untested: {summary.untested}")
        if summary.skipped > 0:
            lines.append(
                f"  Time saved by fail-fast: {summary.time_saved:.2f}s "
                f"(estimated, {summary.skipped} scenario(s) skipped)"
            )

        return "\n".join(lines) + "\n"

    @staticmethod
    def _truncate(text: str, width: int) -> str:
        """Truncate text to width, appending ``...`` if truncated.

        Args:
            text: The text to truncate.
            width: Maximum width in characters.

        Returns:
            Truncated text, or original if it fits.
        """
        if len(text) <= width:
            return text
        if width <= 3:
            return text[:width]
        return text[: width - 3] + "..."

    def summary(self) -> ReportSummary:
        """Compute aggregate statistics.

        The ``time_saved`` estimation uses priority-bucketed averages:
        skipped scenarios are grouped into priority buckets (size 100)
        and each bucket's average executed duration is used as the
        estimate. Buckets without executed scenarios fall back to the
        global average.

        Returns:
            A ``ReportSummary`` with counts, durations, and estimated
            time saved.
        """
        total = len(self._entries)
        passed = sum(1 for e in self._entries if e.status == "passed")
        failed = sum(1 for e in self._entries if e.status == "failed")
        skipped = sum(1 for e in self._entries if e.status == "skipped")
        undefined = sum(1 for e in self._entries if e.status == "undefined")
        known = {"passed", "failed", "skipped", "undefined"}
        untested = sum(1 for e in self._entries if e.status not in known)

        critical_entries = [e for e in self._entries if e.is_critical]
        critical_total = len(critical_entries)
        critical_passed = sum(1 for e in critical_entries if e.status == "passed")
        critical_failed = sum(1 for e in critical_entries if e.status == "failed")
        critical_skipped = sum(1 for e in critical_entries if e.status == "skipped")

        total_duration = sum(e.duration for e in self._entries)
        skipped_duration = sum(e.duration for e in self._entries if e.status == "skipped")
        time_saved = self._estimate_time_saved()

        return ReportSummary(
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            undefined=undefined,
            untested=untested,
            critical_total=critical_total,
            critical_passed=critical_passed,
            critical_failed=critical_failed,
            critical_skipped=critical_skipped,
            total_duration=total_duration,
            skipped_duration=skipped_duration,
            time_saved=time_saved,
        )

    _BUCKET_SIZE = 100

    def _estimate_time_saved(self) -> float:
        """Estimate time saved using priority-bucketed averages.

        Executed (non-skipped) scenarios are grouped into priority
        buckets of size 100. Each skipped scenario's estimated duration
        is the average duration of executed scenarios in the same
        priority bucket. If a bucket has no executed scenarios, the
        global average is used.

        Returns:
            Estimated time saved in seconds.
        """
        executed = [e for e in self._entries if e.status != "skipped"]
        skipped_entries = [e for e in self._entries if e.status == "skipped"]

        if not skipped_entries or not executed:
            return 0.0

        bucket_durations: dict[int, list[float]] = {}
        for e in executed:
            bucket = e.priority // self._BUCKET_SIZE
            bucket_durations.setdefault(bucket, []).append(e.duration)

        bucket_avgs = {
            b: sum(durs) / len(durs) for b, durs in bucket_durations.items()
        }

        global_avg = sum(e.duration for e in executed) / len(executed)

        total = 0.0
        for s in skipped_entries:
            bucket = s.priority // self._BUCKET_SIZE
            total += bucket_avgs.get(bucket, global_avg)

        return total

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dictionary.

        Returns:
            A dict with ``"entries"`` and ``"summary"`` keys.
        """
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
                "untested": summary.untested,
                "critical_total": summary.critical_total,
                "critical_passed": summary.critical_passed,
                "critical_failed": summary.critical_failed,
                "critical_skipped": summary.critical_skipped,
                "total_duration": summary.total_duration,
                "skipped_duration": summary.skipped_duration,
                "pass_rate": summary.pass_rate,
                "time_saved": summary.time_saved,
            },
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize report to a JSON string.

        Args:
            indent: Number of spaces for indentation. Use 0 or negative
                for compact output.

        Returns:
            A JSON string with ``"entries"`` and ``"summary"`` keys.
        """
        return json.dumps(self.to_dict(), indent=indent if indent > 0 else None)

    def to_csv(self) -> str:
        """Serialize report entries to a CSV string.

        The summary is not included in CSV output. Each row represents
        one scenario entry.

        Returns:
            A CSV string with a header row and one row per entry.
        """
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "index",
                "feature_name",
                "scenario_name",
                "priority",
                "status",
                "duration",
                "is_critical",
            ]
        )
        for e in self._entries:
            writer.writerow(
                [
                    e.index,
                    e.feature_name,
                    e.scenario_name,
                    e.priority,
                    e.status,
                    f"{e.duration:.6f}",
                    "true" if e.is_critical else "false",
                ]
            )
        return buf.getvalue()
