"""Unit tests for behave_priority.report."""

from __future__ import annotations

import dataclasses

from behave_priority.config import PriorityConfig
from behave_priority.report import PriorityReport, ReportEntry, ReportSummary


def make_config(**kwargs: object) -> PriorityConfig:
    return PriorityConfig(**kwargs)  # type: ignore[arg-type]


def record_scenario(
    report: PriorityReport,
    name: str = "Scenario 1",
    feature: str = "Feature A",
    priority: int = 1,
    status: str = "passed",
    duration: float = 1.0,
    is_critical: bool = False,
) -> None:
    report.record(
        scenario_name=name,
        feature_name=feature,
        priority=priority,
        status=status,
        duration=duration,
        is_critical=is_critical,
    )


class TestReportEntry:
    def test_is_frozen(self) -> None:
        entry = ReportEntry(
            index=1,
            feature_name="F",
            scenario_name="S",
            priority=1,
            status="passed",
            duration=1.0,
            is_critical=False,
        )
        try:
            entry.status = "failed"  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            pass
        else:
            raise AssertionError("ReportEntry should be frozen")

    def test_has_slots(self) -> None:
        entry = ReportEntry(
            index=1,
            feature_name="F",
            scenario_name="S",
            priority=1,
            status="passed",
            duration=1.0,
            is_critical=False,
        )
        assert not hasattr(entry, "__dict__")

    def test_field_count(self) -> None:
        fields = dataclasses.fields(ReportEntry)
        assert len(fields) == 7

    def test_equality(self) -> None:
        e1 = ReportEntry(1, "F", "S", 1, "passed", 1.0, False)
        e2 = ReportEntry(1, "F", "S", 1, "passed", 1.0, False)
        assert e1 == e2


class TestReportSummary:
    def test_time_saved_alias(self) -> None:
        s = ReportSummary(
            total=10, passed=5, failed=3, skipped=2, undefined=0,
            critical_total=1, critical_passed=1, critical_failed=0,
            total_duration=100.0, skipped_duration=20.0,
        )
        assert s.time_saved == 20.0

    def test_pass_rate_all_passed(self) -> None:
        s = ReportSummary(
            total=10, passed=10, failed=0, skipped=0, undefined=0,
            critical_total=0, critical_passed=0, critical_failed=0,
            total_duration=50.0, skipped_duration=0.0,
        )
        assert s.pass_rate == 100.0

    def test_pass_rate_half(self) -> None:
        s = ReportSummary(
            total=10, passed=5, failed=5, skipped=0, undefined=0,
            critical_total=0, critical_passed=0, critical_failed=0,
            total_duration=50.0, skipped_duration=0.0,
        )
        assert s.pass_rate == 50.0

    def test_pass_rate_excludes_skipped(self) -> None:
        s = ReportSummary(
            total=10, passed=5, failed=3, skipped=2, undefined=0,
            critical_total=0, critical_passed=0, critical_failed=0,
            total_duration=50.0, skipped_duration=10.0,
        )
        assert s.pass_rate == (5 / 8) * 100

    def test_pass_rate_zero_executed(self) -> None:
        s = ReportSummary(
            total=5, passed=0, failed=0, skipped=5, undefined=0,
            critical_total=0, critical_passed=0, critical_failed=0,
            total_duration=25.0, skipped_duration=25.0,
        )
        assert s.pass_rate == 0.0

    def test_is_frozen(self) -> None:
        s = ReportSummary(
            total=1, passed=1, failed=0, skipped=0, undefined=0,
            critical_total=0, critical_passed=0, critical_failed=0,
            total_duration=1.0, skipped_duration=0.0,
        )
        try:
            s.total = 5  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            pass
        else:
            raise AssertionError("ReportSummary should be frozen")

    def test_has_slots(self) -> None:
        s = ReportSummary(
            total=1, passed=1, failed=0, skipped=0, undefined=0,
            critical_total=0, critical_passed=0, critical_failed=0,
            total_duration=1.0, skipped_duration=0.0,
        )
        assert not hasattr(s, "__dict__")


class TestRecord:
    def test_single_record(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="Test 1")
        assert len(report._entries) == 1
        assert report._entries[0].index == 1

    def test_multiple_records_increment_index(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="A")
        record_scenario(report, name="B")
        record_scenario(report, name="C")
        assert report._entries[0].index == 1
        assert report._entries[1].index == 2
        assert report._entries[2].index == 3

    def test_record_stores_all_fields(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(
            report,
            name="Login",
            feature="Auth",
            priority=5,
            status="failed",
            duration=2.5,
            is_critical=True,
        )
        entry = report._entries[0]
        assert entry.scenario_name == "Login"
        assert entry.feature_name == "Auth"
        assert entry.priority == 5
        assert entry.status == "failed"
        assert entry.duration == 2.5
        assert entry.is_critical is True

    def test_record_default_not_critical(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report)
        assert report._entries[0].is_critical is False


class TestSummary:
    def test_empty_report(self) -> None:
        report = PriorityReport(make_config())
        s = report.summary()
        assert s.total == 0
        assert s.passed == 0
        assert s.failed == 0
        assert s.skipped == 0
        assert s.undefined == 0
        assert s.critical_total == 0
        assert s.critical_passed == 0
        assert s.critical_failed == 0
        assert s.total_duration == 0.0
        assert s.skipped_duration == 0.0

    def test_all_passed(self) -> None:
        report = PriorityReport(make_config())
        for i in range(5):
            record_scenario(report, name=f"S{i}", status="passed", duration=1.0)
        s = report.summary()
        assert s.total == 5
        assert s.passed == 5
        assert s.failed == 0
        assert s.skipped == 0
        assert s.total_duration == 5.0

    def test_all_failed(self) -> None:
        report = PriorityReport(make_config())
        for i in range(3):
            record_scenario(report, name=f"S{i}", status="failed", duration=0.5)
        s = report.summary()
        assert s.failed == 3
        assert s.passed == 0

    def test_mixed_statuses(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="p1", status="passed", duration=1.0)
        record_scenario(report, name="f1", status="failed", duration=2.0)
        record_scenario(report, name="s1", status="skipped", duration=0.0)
        record_scenario(report, name="u1", status="undefined", duration=0.5)
        s = report.summary()
        assert s.total == 4
        assert s.passed == 1
        assert s.failed == 1
        assert s.skipped == 1
        assert s.undefined == 1
        assert s.total_duration == 3.5

    def test_critical_stats(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="c1", status="passed", is_critical=True)
        record_scenario(report, name="c2", status="failed", is_critical=True)
        record_scenario(report, name="n1", status="passed", is_critical=False)
        s = report.summary()
        assert s.critical_total == 2
        assert s.critical_passed == 1
        assert s.critical_failed == 1

    def test_no_critical(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="n1", status="passed", is_critical=False)
        s = report.summary()
        assert s.critical_total == 0

    def test_skipped_duration(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="p1", status="passed", duration=2.0)
        record_scenario(report, name="s1", status="skipped", duration=0.0)
        record_scenario(report, name="s2", status="skipped", duration=0.0)
        s = report.summary()
        assert s.skipped == 2
        assert s.skipped_duration == 0.0
        assert s.total_duration == 2.0

    def test_skipped_with_duration(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="p1", status="passed", duration=3.0)
        record_scenario(report, name="s1", status="skipped", duration=1.5)
        s = report.summary()
        assert s.skipped_duration == 1.5
        assert s.total_duration == 4.5


class TestRender:
    def test_empty_report_render(self) -> None:
        report = PriorityReport(make_config())
        output = report.render()
        assert "Priority Execution Report" in output
        assert "No scenarios executed" in output

    def test_render_has_header(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report)
        output = report.render()
        assert "Priority Execution Report" in output
        assert "===" in output
        assert "Feature" in output
        assert "Scenario" in output
        assert "Status" in output
        assert "Duration" in output

    def test_render_has_entry(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(
            report,
            name="Login test",
            feature="Auth",
            priority=1,
            status="passed",
            duration=1.5,
        )
        output = report.render()
        assert "Login test" in output
        assert "Auth" in output
        assert "passed" in output

    def test_render_has_summary(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="s1", status="passed")
        record_scenario(report, name="s2", status="failed")
        output = report.render()
        assert "Summary:" in output
        assert "1 passed" in output
        assert "1 failed" in output

    def test_render_critical_summary(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="c1", status="passed", is_critical=True)
        record_scenario(report, name="c2", status="failed", is_critical=True)
        output = report.render()
        assert "Critical:" in output
        assert "1/2 passed" in output

    def test_render_no_critical_section_when_none(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, is_critical=False)
        output = report.render()
        assert "Critical:" not in output

    def test_render_skipped_info(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="p1", status="passed", duration=2.0)
        record_scenario(report, name="s1", status="skipped", duration=1.0)
        output = report.render()
        assert "Time saved" in output
        assert "1 scenario(s) skipped" in output

    def test_render_no_skipped_info_when_none_skipped(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed")
        output = report.render()
        assert "Time saved" not in output

    def test_render_long_feature_name_truncated(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(
            report,
            feature="A" * 50,
            name="S",
        )
        output = report.render()
        assert "..." in output

    def test_render_long_scenario_name_truncated(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(
            report,
            name="S" * 50,
        )
        output = report.render()
        assert "..." in output

    def test_render_ends_with_newline(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report)
        output = report.render()
        assert output.endswith("\n")


class TestToDict:
    def test_empty_dict(self) -> None:
        report = PriorityReport(make_config())
        d = report.to_dict()
        assert d["entries"] == []
        assert d["summary"]["total"] == 0

    def test_entries_serialized(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(
            report,
            name="Login",
            feature="Auth",
            priority=1,
            status="passed",
            duration=2.5,
            is_critical=True,
        )
        d = report.to_dict()
        assert len(d["entries"]) == 1
        entry = d["entries"][0]
        assert entry["scenario_name"] == "Login"
        assert entry["feature_name"] == "Auth"
        assert entry["priority"] == 1
        assert entry["status"] == "passed"
        assert entry["duration"] == 2.5
        assert entry["is_critical"] is True
        assert entry["index"] == 1

    def test_multiple_entries(self) -> None:
        report = PriorityReport(make_config())
        for i in range(5):
            record_scenario(report, name=f"S{i}")
        d = report.to_dict()
        assert len(d["entries"]) == 5
        for i, entry in enumerate(d["entries"]):
            assert entry["index"] == i + 1

    def test_summary_in_dict(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed", duration=1.0)
        record_scenario(report, status="failed", duration=2.0)
        record_scenario(report, status="skipped", duration=0.5, is_critical=True)
        d = report.to_dict()
        s = d["summary"]
        assert s["total"] == 3
        assert s["passed"] == 1
        assert s["failed"] == 1
        assert s["skipped"] == 1
        assert s["total_duration"] == 3.5
        assert s["skipped_duration"] == 0.5

    def test_dict_has_entries_and_summary_keys(self) -> None:
        report = PriorityReport(make_config())
        d = report.to_dict()
        assert "entries" in d
        assert "summary" in d
