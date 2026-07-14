"""Unit tests for behave_priority.report."""

from __future__ import annotations

import dataclasses

import pytest

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
    def test_time_saved_defaults_to_zero(self) -> None:
        s = ReportSummary(
            total=10, passed=5, failed=3, skipped=2, undefined=0,
            critical_total=1, critical_passed=1, critical_failed=0,
            total_duration=100.0, skipped_duration=0.0,
        )
        assert s.time_saved == 0.0

    def test_time_saved_zero_when_no_skipped(self) -> None:
        s = ReportSummary(
            total=5, passed=5, failed=0, skipped=0, undefined=0,
            critical_total=0, critical_passed=0, critical_failed=0,
            total_duration=50.0, skipped_duration=0.0,
        )
        assert s.time_saved == 0.0

    def test_time_saved_zero_when_all_skipped(self) -> None:
        s = ReportSummary(
            total=5, passed=0, failed=0, skipped=5, undefined=0,
            critical_total=0, critical_passed=0, critical_failed=0,
            total_duration=0.0, skipped_duration=0.0,
        )
        assert s.time_saved == 0.0

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

    def test_render_short_names_no_truncation(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, feature="Auth", name="Login")
        output = report.render()
        assert "Auth" in output
        assert "Login" in output
        assert "..." not in output

    def test_render_dynamic_width_fits_content(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, feature="MyFeature", name="MyScenario")
        output = report.render()
        assert "MyFeature" in output
        assert "MyScenario" in output

    def test_render_width_capped_at_40(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, feature="F" * 100, name="S" * 100)
        output = report.render()
        assert "..." in output
        for line in output.split("\n"):
            assert len(line) < 120

    def test_render_truncate_preserves_short_names(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, feature="AB", name="CD")
        output = report.render()
        assert "AB" in output
        assert "CD" in output

    def test_render_mixed_short_and_long_names(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, feature="Short", name="S")
        record_scenario(report, feature="X" * 60, name="Y" * 60)
        output = report.render()
        assert "Short" in output
        assert "..." in output

    def test_render_short_names_header_aligned(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, feature="AB", name="CD")
        output = report.render()
        lines = output.split("\n")
        header_line = [ln for ln in lines if ln.startswith("  #")][0]
        data_line = [ln for ln in lines if "AB" in ln and "CD" in ln][0]
        assert len(header_line) == len(data_line)

    def test_truncate_fits(self) -> None:
        assert PriorityReport._truncate("hello", 10) == "hello"

    def test_truncate_exact_fit(self) -> None:
        assert PriorityReport._truncate("hello", 5) == "hello"

    def test_truncate_with_ellipsis(self) -> None:
        assert PriorityReport._truncate("hello world", 8) == "hello..."

    def test_truncate_small_width(self) -> None:
        assert PriorityReport._truncate("hello", 3) == "hel"

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
        assert s["pass_rate"] == 50.0
        assert s["time_saved"] == pytest.approx(1.5)

    def test_dict_has_entries_and_summary_keys(self) -> None:
        report = PriorityReport(make_config())
        d = report.to_dict()
        assert "entries" in d
        assert "summary" in d

    def test_dict_includes_pass_rate(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed")
        record_scenario(report, status="passed")
        record_scenario(report, status="failed")
        d = report.to_dict()
        assert d["summary"]["pass_rate"] == pytest.approx(66.67, rel=1e-2)

    def test_dict_includes_time_saved(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed", duration=2.0)
        record_scenario(report, status="skipped", duration=0.0)
        d = report.to_dict()
        assert d["summary"]["time_saved"] == pytest.approx(2.0)

    def test_dict_pass_rate_zero_when_all_skipped(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="skipped")
        record_scenario(report, status="skipped")
        d = report.to_dict()
        assert d["summary"]["pass_rate"] == 0.0

    def test_dict_pass_rate_zero_when_empty(self) -> None:
        report = PriorityReport(make_config())
        d = report.to_dict()
        assert d["summary"]["pass_rate"] == 0.0
        assert d["summary"]["time_saved"] == 0.0


class TestToJson:
    """Tests for PriorityReport.to_json()."""

    def test_empty_report_json(self) -> None:
        report = PriorityReport(make_config())
        import json

        data = json.loads(report.to_json())
        assert data["entries"] == []
        assert data["summary"]["total"] == 0

    def test_json_contains_entries(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="Alpha", status="passed")
        record_scenario(report, name="Beta", status="failed")
        import json

        data = json.loads(report.to_json())
        assert len(data["entries"]) == 2
        assert data["entries"][0]["scenario_name"] == "Alpha"
        assert data["entries"][1]["scenario_name"] == "Beta"

    def test_json_contains_summary(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed")
        record_scenario(report, status="failed")
        record_scenario(report, status="skipped")
        import json

        data = json.loads(report.to_json())
        assert data["summary"]["total"] == 3
        assert data["summary"]["passed"] == 1
        assert data["summary"]["failed"] == 1
        assert data["summary"]["skipped"] == 1

    def test_json_compact_mode(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="Alpha")
        compact = report.to_json(indent=0)
        assert "\n" not in compact

    def test_json_pretty_mode(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="Alpha")
        pretty = report.to_json(indent=2)
        assert "\n" in pretty


class TestToCsv:
    """Tests for PriorityReport.to_csv()."""

    def test_empty_report_csv(self) -> None:
        report = PriorityReport(make_config())
        csv_output = report.to_csv()
        lines = csv_output.strip().splitlines()
        assert len(lines) == 1
        assert "index" in lines[0]
        assert "scenario_name" in lines[0]

    def test_csv_contains_entries(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="Alpha", status="passed", duration=1.5)
        record_scenario(report, name="Beta", status="failed", duration=0.5)
        csv_output = report.to_csv()
        lines = csv_output.strip().splitlines()
        assert len(lines) == 3
        assert "Alpha" in lines[1]
        assert "Beta" in lines[2]
        assert "passed" in lines[1]
        assert "failed" in lines[2]

    def test_csv_header_columns(self) -> None:
        report = PriorityReport(make_config())
        csv_output = report.to_csv()
        header = csv_output.splitlines()[0]
        assert "index" in header
        assert "feature_name" in header
        assert "scenario_name" in header
        assert "priority" in header
        assert "status" in header
        assert "duration" in header
        assert "is_critical" in header

    def test_csv_includes_critical_flag(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, name="Critical", is_critical=True)
        record_scenario(report, name="Normal", is_critical=False)
        csv_output = report.to_csv()
        lines = csv_output.strip().splitlines()
        assert ",true" in lines[1]
        assert ",false" in lines[2]


class TestReportFormatConfig:
    """Tests for report_format validation in PriorityConfig."""

    def test_default_format_is_text(self) -> None:
        config = PriorityConfig()
        assert config.report_format == "text"

    def test_json_format_accepted(self) -> None:
        config = PriorityConfig(report_format="json")
        assert config.report_format == "json"

    def test_csv_format_accepted(self) -> None:
        config = PriorityConfig(report_format="csv")
        assert config.report_format == "csv"

    def test_invalid_format_rejected(self) -> None:
        with pytest.raises(ValueError, match="report_format"):
            PriorityConfig(report_format="xml")  # type: ignore[arg-type]


class TestTimeSavedEstimation:
    """Tests for priority-bucketed time_saved estimation."""

    def test_zero_when_no_skipped(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed", duration=1.0)
        record_scenario(report, status="failed", duration=2.0)
        assert report.summary().time_saved == 0.0

    def test_zero_when_no_executed(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="skipped", duration=0.0)
        record_scenario(report, status="skipped", duration=0.0)
        assert report.summary().time_saved == 0.0

    def test_zero_when_empty(self) -> None:
        report = PriorityReport(make_config())
        assert report.summary().time_saved == 0.0

    def test_same_bucket_uses_bucket_avg(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed", duration=2.0, priority=1)
        record_scenario(report, status="passed", duration=4.0, priority=50)
        record_scenario(report, status="skipped", duration=0.0, priority=10)
        s = report.summary()
        assert s.time_saved == pytest.approx(3.0)

    def test_different_buckets_use_own_avg(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed", duration=1.0, priority=1)
        record_scenario(report, status="passed", duration=10.0, priority=200)
        record_scenario(report, status="skipped", duration=0.0, priority=5)
        record_scenario(report, status="skipped", duration=0.0, priority=250)
        s = report.summary()
        assert s.time_saved == pytest.approx(11.0)

    def test_bucket_without_executed_falls_back_to_global(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed", duration=2.0, priority=1)
        record_scenario(report, status="passed", duration=4.0, priority=2)
        record_scenario(report, status="skipped", duration=0.0, priority=500)
        s = report.summary()
        global_avg = (2.0 + 4.0) / 2
        assert s.time_saved == pytest.approx(global_avg)

    def test_multiple_skipped_in_same_bucket(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed", duration=3.0, priority=1)
        record_scenario(report, status="skipped", duration=0.0, priority=10)
        record_scenario(report, status="skipped", duration=0.0, priority=20)
        record_scenario(report, status="skipped", duration=0.0, priority=30)
        s = report.summary()
        assert s.time_saved == pytest.approx(9.0)

    def test_mixed_buckets(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="passed", duration=2.0, priority=1)
        record_scenario(report, status="passed", duration=8.0, priority=150)
        record_scenario(report, status="skipped", duration=0.0, priority=50)
        record_scenario(report, status="skipped", duration=0.0, priority=180)
        record_scenario(report, status="skipped", duration=0.0, priority=999)
        s = report.summary()
        global_avg = (2.0 + 8.0) / 2
        assert s.time_saved == pytest.approx(2.0 + 8.0 + global_avg)

    def test_failed_scenarios_count_as_executed(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="failed", duration=5.0, priority=1)
        record_scenario(report, status="skipped", duration=0.0, priority=10)
        s = report.summary()
        assert s.time_saved == pytest.approx(5.0)

    def test_undefined_scenarios_count_as_executed(self) -> None:
        report = PriorityReport(make_config())
        record_scenario(report, status="undefined", duration=3.0, priority=1)
        record_scenario(report, status="skipped", duration=0.0, priority=10)
        s = report.summary()
        assert s.time_saved == pytest.approx(3.0)
