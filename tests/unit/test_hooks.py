"""Unit tests for behave_priority.hooks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from behave_priority.config import PriorityConfig
from behave_priority.hooks import (
    PriorityState,
    _scenario_key,
    after_scenario_hook,
    before_scenario_hook,
    get_report,
    priority_report,
    setup_priority,
)
from behave_priority.report import PriorityReport
from behave_priority.sorter import ScenarioSorter


@dataclass
class FakeScenario:
    name: str
    tags: list[str] = field(default_factory=list)
    status: str = "passed"
    duration: float = 0.0
    skipped: bool = False
    skip_reason: str = ""
    filename: str | None = None
    line: int | None = None

    def skip(self, reason: str) -> None:
        self.skipped = True
        self.skip_reason = reason
        self.status = "skipped"


@dataclass
class FakeFeature:
    name: str | None
    filename: str
    tags: list[str] = field(default_factory=list)
    scenarios: list[FakeScenario] = field(default_factory=list)
    run_items: list[Any] | None = None


@dataclass
class FakeRule:
    name: str
    tags: list[str] = field(default_factory=list)
    scenarios: list[FakeScenario] = field(default_factory=list)
    run_items: list[FakeScenario] | None = None


@dataclass
class FakeRunner:
    features: list[FakeFeature] = field(default_factory=list)


@dataclass
class FakeContext:
    _runner: Any = None
    runner: Any = None
    _priority_state: Any = None


def make_state(config: PriorityConfig | None = None) -> PriorityState:
    if config is None:
        config = PriorityConfig()
    return PriorityState(
        config=config,
        report=PriorityReport(config),
        sorter=ScenarioSorter(config),
    )


class TestPriorityStateDefaults:
    def test_defaults(self) -> None:
        state = make_state()
        assert state.failed_count == 0
        assert state.critical_failed is False
        assert state.should_stop is False
        assert state.executed_count == 0
        assert state.skipped_count == 0
        assert state.priority_map == {}
        assert state.feature_map == {}

    def test_has_config(self) -> None:
        config = PriorityConfig(order=True)
        state = make_state(config)
        assert state.config is config

    def test_has_report(self) -> None:
        state = make_state()
        assert isinstance(state.report, PriorityReport)

    def test_has_sorter(self) -> None:
        state = make_state()
        assert isinstance(state.sorter, ScenarioSorter)


class TestCheckFailFast:
    def test_no_stop_conditions(self) -> None:
        state = make_state()
        assert state.check_fail_fast() is False

    def test_stop_after_failures_not_reached(self) -> None:
        state = make_state(PriorityConfig(stop_after_failures=3))
        state.failed_count = 2
        assert state.check_fail_fast() is False

    def test_stop_after_failures_reached(self) -> None:
        state = make_state(PriorityConfig(stop_after_failures=3))
        state.failed_count = 3
        assert state.check_fail_fast() is True

    def test_stop_after_failures_exceeded(self) -> None:
        state = make_state(PriorityConfig(stop_after_failures=2))
        state.failed_count = 5
        assert state.check_fail_fast() is True

    def test_stop_after_failures_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="stop_after_failures"):
            PriorityConfig(stop_after_failures=0)

    def test_stop_after_failures_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="stop_after_failures"):
            PriorityConfig(stop_after_failures=-1)

    def test_stop_on_critical_not_failed(self) -> None:
        state = make_state(PriorityConfig(stop_on_critical=True))
        assert state.check_fail_fast() is False

    def test_stop_on_critical_failed(self) -> None:
        state = make_state(PriorityConfig(stop_on_critical=True))
        state.critical_failed = True
        assert state.check_fail_fast() is True

    def test_stop_on_critical_without_flag(self) -> None:
        state = make_state(PriorityConfig(stop_on_critical=False))
        state.critical_failed = True
        assert state.check_fail_fast() is False

    def test_both_conditions(self) -> None:
        state = make_state(
            PriorityConfig(stop_after_failures=2, stop_on_critical=True)
        )
        state.failed_count = 2
        state.critical_failed = True
        assert state.check_fail_fast() is True

    def test_either_condition_satisfies(self) -> None:
        state = make_state(
            PriorityConfig(stop_after_failures=5, stop_on_critical=True)
        )
        state.critical_failed = True
        assert state.check_fail_fast() is True


class TestSetupPriority:
    def test_sets_up_state_on_context(self) -> None:
        s1 = FakeScenario("s1", tags=["priority(1)"])
        s2 = FakeScenario("s2", tags=["priority(2)"])
        feature = FakeFeature("F", "f.feature", scenarios=[s2, s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, order=True)
        assert ctx._priority_state is not None
        assert isinstance(ctx._priority_state, PriorityState)

    def test_sorts_scenarios(self) -> None:
        s1 = FakeScenario("low", tags=["priority(3)"])
        s2 = FakeScenario("high", tags=["priority(1)"])
        feature = FakeFeature("F", "f.feature", scenarios=[s1, s2])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, order=True)
        assert runner.features[0].scenarios == [s2, s1]

    def test_populates_priority_map(self) -> None:
        s1 = FakeScenario("a", tags=["priority(1)"])
        s2 = FakeScenario("b", tags=["priority(5)"])
        feature = FakeFeature("F", "f.feature", scenarios=[s1, s2])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx)
        state = ctx._priority_state
        assert state.priority_map[_scenario_key(s1)] == 1
        assert state.priority_map[_scenario_key(s2)] == 5

    def test_no_runner_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        ctx = FakeContext(_runner=None, runner=None)
        with caplog.at_level(logging.WARNING, logger="behave_priority.hooks"):
            setup_priority(ctx)
        assert "cannot access behave's runner" in caplog.text
        assert ctx._priority_state is None

    def test_no_features_returns_silently(self) -> None:
        runner = FakeRunner(features=[])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx)
        assert ctx._priority_state is not None

    def test_no_features_attr_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        ctx = FakeContext(_runner=object())
        with caplog.at_level(logging.WARNING, logger="behave_priority.hooks"):
            setup_priority(ctx)
        assert "no 'features'" in caplog.text
        assert ctx._priority_state is None

    def test_runner_via_runner_attr(self) -> None:
        s1 = FakeScenario("s1")
        feature = FakeFeature("F", "f.feature", scenarios=[s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=None, runner=runner)
        setup_priority(ctx)
        assert ctx._priority_state is not None

    def test_config_passed_through(self) -> None:
        s1 = FakeScenario("s1")
        feature = FakeFeature("F", "f.feature", scenarios=[s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(
            ctx,
            order=True,
            reverse=True,
            stop_after_failures=5,
            stop_on_critical=True,
            critical_tag="critico",
            default_priority=100,
            report=True,
        )
        state = ctx._priority_state
        assert state.config.order is True
        assert state.config.reverse is True
        assert state.config.stop_after_failures == 5
        assert state.config.stop_on_critical is True
        assert state.config.critical_tag == "critico"
        assert state.config.default_priority == 100
        assert state.config.report is True

    def test_priority_tag_param(self) -> None:
        s1 = FakeScenario("smoke", tags=["smoke"])
        s2 = FakeScenario("normal")
        feature = FakeFeature("F", "f.feature", scenarios=[s2, s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, priority_tag="smoke")
        state = ctx._priority_state
        assert state.config.priority_tag == "smoke"

    def test_feature_priority_in_map(self) -> None:
        s1 = FakeScenario("no_tag")
        feature = FakeFeature(
            "F", "f.feature", tags=["feature-priority(3)"], scenarios=[s1]
        )
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx)
        state = ctx._priority_state
        assert state.priority_map[_scenario_key(s1)] == 3

    def test_default_priority_in_map(self) -> None:
        s1 = FakeScenario("no_tag")
        feature = FakeFeature("F", "f.feature", scenarios=[s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, default_priority=42)
        state = ctx._priority_state
        assert state.priority_map[_scenario_key(s1)] == 42

    def test_feature_map_populated(self) -> None:
        s1 = FakeScenario("a")
        s2 = FakeScenario("b")
        feature = FakeFeature("MyFeature", "f.feature", scenarios=[s1, s2])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx)
        state = ctx._priority_state
        assert state.feature_map[_scenario_key(s1)] == "MyFeature"
        assert state.feature_map[_scenario_key(s2)] == "MyFeature"

    def test_feature_map_uses_filename_when_name_is_none(self) -> None:
        s1 = FakeScenario("a")
        feature = FakeFeature(None, "path/to/f.feature", scenarios=[s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx)
        state = ctx._priority_state
        assert state.feature_map[_scenario_key(s1)] == "path/to/f.feature"


class TestBeforeScenarioHook:
    def test_no_state_does_nothing(self) -> None:
        ctx = FakeContext(_priority_state=None)
        scenario = FakeScenario("s")
        before_scenario_hook(ctx, scenario)
        assert scenario.skipped is False

    def test_should_stop_skips_scenario(self) -> None:
        state = make_state()
        state.should_stop = True
        ctx = FakeContext(_priority_state=state)
        scenario = FakeScenario("s")
        before_scenario_hook(ctx, scenario)
        assert scenario.skipped is True
        assert scenario.skip_reason == "fail-fast triggered"
        assert len(state.report._entries) == 0

    def test_should_not_stop_does_not_skip(self) -> None:
        state = make_state()
        ctx = FakeContext(_priority_state=state)
        scenario = FakeScenario("s")
        before_scenario_hook(ctx, scenario)
        assert scenario.skipped is False
        assert len(state.report._entries) == 0

    def test_should_stop_increments_skipped_count(self) -> None:
        state = make_state()
        state.should_stop = True
        ctx = FakeContext(_priority_state=state)
        scenario = FakeScenario("s")
        before_scenario_hook(ctx, scenario)
        assert state.skipped_count == 1
        assert scenario.skipped is True
        assert len(state.report._entries) == 0

    def test_coordinator_triggers_skip_before_scenario(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from behave_priority.parallel import ParallelCoordinator

        config = PriorityConfig(stop_after_failures=1, parallel_coord=True)
        state = make_state(config)
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        state.coordinator = coord
        ctx = FakeContext(_priority_state=state)
        scenario = FakeScenario("s")
        before_scenario_hook(ctx, scenario)
        assert scenario.skipped is False

        other = ParallelCoordinator(tmp_path, worker_id="w2")
        other.report_failure()

        scenario2 = FakeScenario("s2")
        before_scenario_hook(ctx, scenario2)
        assert scenario2.skipped is True
        assert state.should_stop is True
        coord.cleanup()
        other.cleanup()

    def test_skipped_records_feature_name(self) -> None:
        state = make_state()
        scenario = FakeScenario("s", status="skipped")
        state.feature_map[_scenario_key(scenario)] = "MyFeature"
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        assert state.report._entries[0].feature_name == "MyFeature"

    def test_skipped_records_priority_from_map(self) -> None:
        state = make_state()
        scenario = FakeScenario("s", tags=["priority(3)"], status="skipped")
        state.priority_map[_scenario_key(scenario)] = 3
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        assert state.report._entries[0].priority == 3

    def test_skipped_records_default_priority(self) -> None:
        state = make_state(PriorityConfig(default_priority=42))
        scenario = FakeScenario("s", status="skipped")
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        assert state.report._entries[0].priority == 42

    def test_skipped_records_critical_tag(self) -> None:
        state = make_state()
        scenario = FakeScenario("s", tags=["critical"], status="skipped")
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        assert state.report._entries[0].is_critical is True

    def test_skipped_records_scenario_name(self) -> None:
        state = make_state()
        scenario = FakeScenario("My Skipped Test", status="skipped")
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        assert state.report._entries[0].scenario_name == "My Skipped Test"


class TestAfterScenarioHook:
    def test_no_state_does_nothing(self) -> None:
        ctx = FakeContext(_priority_state=None)
        scenario = FakeScenario("s")
        after_scenario_hook(ctx, scenario)

    def test_records_passed(self) -> None:
        state = make_state()
        ctx = FakeContext(_priority_state=state)
        scenario = FakeScenario("s", status="passed", duration=1.5)
        after_scenario_hook(ctx, scenario)
        assert state.executed_count == 1
        assert state.failed_count == 0
        entries = state.report._entries
        assert len(entries) == 1
        assert entries[0].status == "passed"
        assert entries[0].duration == 1.5

    def test_records_failed(self) -> None:
        state = make_state()
        ctx = FakeContext(_priority_state=state)
        scenario = FakeScenario("s", status="failed", duration=2.0)
        after_scenario_hook(ctx, scenario)
        assert state.failed_count == 1
        assert state.should_stop is False

    def test_records_critical_failure(self) -> None:
        state = make_state(PriorityConfig(stop_on_critical=True))
        ctx = FakeContext(_priority_state=state)
        scenario = FakeScenario(
            "s", status="failed", tags=["critical"], duration=1.0
        )
        after_scenario_hook(ctx, scenario)
        assert state.critical_failed is True
        assert state.should_stop is True

    def test_triggers_fail_fast_after_threshold(self) -> None:
        state = make_state(PriorityConfig(stop_after_failures=2))
        ctx = FakeContext(_priority_state=state)
        s1 = FakeScenario("s1", status="failed")
        s2 = FakeScenario("s2", status="failed")
        after_scenario_hook(ctx, s1)
        assert state.should_stop is False
        after_scenario_hook(ctx, s2)
        assert state.should_stop is True

    def test_records_priority_from_map(self) -> None:
        state = make_state()
        scenario = FakeScenario("s", tags=["priority(5)"])
        state.priority_map[_scenario_key(scenario)] = 5
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        entries = state.report._entries
        assert entries[0].priority == 5

    def test_records_default_priority_when_not_in_map(self) -> None:
        state = make_state(PriorityConfig(default_priority=42))
        scenario = FakeScenario("s")
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        entries = state.report._entries
        assert entries[0].priority == 42

    def test_finds_feature_name(self) -> None:
        state = make_state()
        scenario = FakeScenario("s")
        state.feature_map[_scenario_key(scenario)] = "MyFeature"
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        entries = state.report._entries
        assert entries[0].feature_name == "MyFeature"

    def test_feature_name_fallback_to_filename(self) -> None:
        state = make_state()
        scenario = FakeScenario("s")
        state.feature_map[_scenario_key(scenario)] = "path/to/feature.feature"
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        entries = state.report._entries
        assert entries[0].feature_name == "path/to/feature.feature"

    def test_critical_tag_detected(self) -> None:
        state = make_state(PriorityConfig(critical_tag="critico"))
        scenario = FakeScenario("s", tags=["critico"])
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        entries = state.report._entries
        assert entries[0].is_critical is True

    def test_not_critical(self) -> None:
        state = make_state()
        scenario = FakeScenario("s", tags=["smoke"])
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        entries = state.report._entries
        assert entries[0].is_critical is False

    def test_scenario_name_recorded(self) -> None:
        state = make_state()
        scenario = FakeScenario("My Test Scenario")
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        entries = state.report._entries
        assert entries[0].scenario_name == "My Test Scenario"

    def test_skipped_status_does_not_fail(self) -> None:
        state = make_state(PriorityConfig(stop_after_failures=1))
        ctx = FakeContext(_priority_state=state)
        scenario = FakeScenario("s", status="skipped")
        after_scenario_hook(ctx, scenario)
        assert state.failed_count == 0
        assert state.executed_count == 0
        assert state.should_stop is False


class TestPriorityReportFunction:
    def test_no_state_does_nothing(self, caplog: pytest.LogCaptureFixture) -> None:
        ctx = FakeContext(_priority_state=None)
        with caplog.at_level(logging.INFO, logger="behave_priority.hooks"):
            priority_report(ctx)
        assert caplog.text == ""

    def test_prints_when_report_enabled(self, caplog: pytest.LogCaptureFixture) -> None:
        state = make_state(PriorityConfig(report=True))
        ctx = FakeContext(_priority_state=state)
        with caplog.at_level(logging.INFO, logger="behave_priority.hooks"):
            priority_report(ctx)
        assert "Priority Execution Report" in caplog.text

    def test_does_not_print_when_report_disabled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        state = make_state(PriorityConfig(report=False))
        ctx = FakeContext(_priority_state=state)
        with caplog.at_level(logging.INFO, logger="behave_priority.hooks"):
            priority_report(ctx)
        assert caplog.text == ""

    def test_json_format_outputs_json(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        state = make_state(PriorityConfig(report=True, report_format="json"))
        ctx = FakeContext(_priority_state=state)
        with caplog.at_level(logging.INFO, logger="behave_priority.hooks"):
            priority_report(ctx)
        import json as json_mod

        messages = [r.getMessage() for r in caplog.records]
        text = "\n".join(messages).strip()
        data = json_mod.loads(text)
        assert "entries" in data
        assert "summary" in data

    def test_csv_format_outputs_csv(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        state = make_state(PriorityConfig(report=True, report_format="csv"))
        ctx = FakeContext(_priority_state=state)
        with caplog.at_level(logging.INFO, logger="behave_priority.hooks"):
            priority_report(ctx)
        messages = [r.getMessage() for r in caplog.records]
        text = "\n".join(messages).strip()
        assert "index" in text
        assert "scenario_name" in text
        assert "status" in text


class TestGetReport:
    def test_no_state_returns_none(self) -> None:
        ctx = FakeContext(_priority_state=None)
        assert get_report(ctx) is None

    def test_returns_report_when_state_exists(self) -> None:
        state = make_state()
        ctx = FakeContext(_priority_state=state)
        report = get_report(ctx)
        assert report is not None
        assert report is state.report

    def test_returns_report_with_entries(self) -> None:
        state = make_state()
        scenario = FakeScenario("s", status="passed", duration=1.0)
        ctx = FakeContext(_priority_state=state)
        after_scenario_hook(ctx, scenario)
        report = get_report(ctx)
        assert report is not None
        summary = report.summary()
        assert summary.total == 1
        assert summary.passed == 1

    def test_returns_none_without_setup(self) -> None:
        ctx = FakeContext()
        assert get_report(ctx) is None


class TestIntegrationFlow:
    def test_full_flow_sort_failfast_skip(self) -> None:
        s1 = FakeScenario("high", tags=["priority(1)"])
        s2 = FakeScenario("mid", tags=["priority(2)"])
        s3 = FakeScenario("low", tags=["priority(3)"])
        feature = FakeFeature("F", "f.feature", scenarios=[s3, s2, s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)

        setup_priority(ctx, order=True, stop_after_failures=1, report=True)
        state = ctx._priority_state

        assert runner.features[0].scenarios == [s1, s2, s3]

        s1.status = "failed"
        s1.duration = 1.0
        after_scenario_hook(ctx, s1)
        assert state.should_stop is True

        before_scenario_hook(ctx, s2)
        assert s2.skipped is True
        s2.status = "skipped"
        after_scenario_hook(ctx, s2)

        before_scenario_hook(ctx, s3)
        assert s3.skipped is True
        s3.status = "skipped"
        after_scenario_hook(ctx, s3)

        summary = state.report.summary()
        assert summary.total == 3
        assert summary.failed == 1
        assert summary.skipped == 2

    def test_full_flow_critical_stop(self) -> None:
        s1 = FakeScenario("critical_test", tags=["priority(1)", "critical"])
        s2 = FakeScenario("normal", tags=["priority(2)"])
        feature = FakeFeature("F", "f.feature", scenarios=[s2, s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)

        setup_priority(ctx, order=True, stop_on_critical=True)
        state = ctx._priority_state

        assert runner.features[0].scenarios == [s1, s2]

        s1.status = "failed"
        s1.duration = 0.5
        after_scenario_hook(ctx, s1)
        assert state.critical_failed is True
        assert state.should_stop is True

        before_scenario_hook(ctx, s2)
        assert s2.skipped is True
        s2.status = "skipped"
        after_scenario_hook(ctx, s2)

        summary = state.report.summary()
        assert summary.total == 2
        assert summary.failed == 1
        assert summary.skipped == 1

    def test_full_flow_no_failfast_all_pass(self) -> None:
        s1 = FakeScenario("a", tags=["priority(1)"])
        s2 = FakeScenario("b", tags=["priority(2)"])
        feature = FakeFeature("F", "f.feature", scenarios=[s2, s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)

        setup_priority(ctx, order=True)
        state = ctx._priority_state

        assert runner.features[0].scenarios == [s1, s2]

        s1.status = "passed"
        s1.duration = 1.0
        after_scenario_hook(ctx, s1)
        assert state.should_stop is False

        before_scenario_hook(ctx, s2)
        assert s2.skipped is False

        s2.status = "passed"
        s2.duration = 2.0
        after_scenario_hook(ctx, s2)
        assert state.should_stop is False

        summary = state.report.summary()
        assert summary.total == 2
        assert summary.passed == 2


class TestScenarioKey:
    def test_deterministic_key_with_filename_and_line(self) -> None:
        s = FakeScenario("s", filename="features/test.feature", line=10)
        assert _scenario_key(s) == "features/test.feature:10"

    def test_deterministic_key_different_lines(self) -> None:
        s1 = FakeScenario("s1", filename="f.feature", line=5)
        s2 = FakeScenario("s2", filename="f.feature", line=10)
        assert _scenario_key(s1) != _scenario_key(s2)

    def test_deterministic_key_different_filenames(self) -> None:
        s1 = FakeScenario("s1", filename="a.feature", line=5)
        s2 = FakeScenario("s2", filename="b.feature", line=5)
        assert _scenario_key(s1) != _scenario_key(s2)

    def test_fallback_to_id_when_no_filename(self) -> None:
        s = FakeScenario("s", line=10)
        key = _scenario_key(s)
        assert key.startswith("id:")

    def test_fallback_to_id_when_no_line(self) -> None:
        s = FakeScenario("s", filename="f.feature")
        key = _scenario_key(s)
        assert key.startswith("id:")

    def test_fallback_to_id_when_neither(self) -> None:
        s = FakeScenario("s")
        key = _scenario_key(s)
        assert key.startswith("id:")

    def test_deterministic_key_stable_across_calls(self) -> None:
        s = FakeScenario("s", filename="f.feature", line=3)
        assert _scenario_key(s) == _scenario_key(s)

    def test_setup_uses_deterministic_keys(self) -> None:
        s1 = FakeScenario("a", tags=["priority(1)"], filename="f.feature", line=5)
        s2 = FakeScenario("b", tags=["priority(2)"], filename="f.feature", line=10)
        feature = FakeFeature("F", "f.feature", scenarios=[s1, s2])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx)
        state = ctx._priority_state
        assert state.priority_map["f.feature:5"] == 1
        assert state.priority_map["f.feature:10"] == 2
        assert state.feature_map["f.feature:5"] == "F"
        assert state.feature_map["f.feature:10"] == "F"


class TestRuleSupport:
    def test_setup_populates_rule_scenarios_in_priority_map(self) -> None:
        s1 = FakeScenario("s1", tags=["priority(1)"], filename="f.feature", line=5)
        s2 = FakeScenario("s2", filename="f.feature", line=10)
        rule = FakeRule("R", tags=["priority(3)"], run_items=[s1, s2], scenarios=[s1, s2])
        feature = FakeFeature("F", "f.feature", run_items=[rule], scenarios=[s1, s2])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, order=True)
        state = ctx._priority_state
        assert state.priority_map["f.feature:5"] == 1
        assert state.priority_map["f.feature:10"] == 3

    def test_setup_populates_feature_map_for_rule_scenarios(self) -> None:
        s1 = FakeScenario("s1", filename="f.feature", line=5)
        rule = FakeRule("R", run_items=[s1], scenarios=[s1])
        feature = FakeFeature("F", "f.feature", run_items=[rule], scenarios=[s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, order=True)
        state = ctx._priority_state
        assert state.feature_map["f.feature:5"] == "F"

    def test_setup_rule_tags_provide_priority(self) -> None:
        s1 = FakeScenario("s1", filename="f.feature", line=5)
        rule = FakeRule("R", tags=["priority(2)"], run_items=[s1], scenarios=[s1])
        feature = FakeFeature("F", "f.feature", run_items=[rule], scenarios=[s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, order=True)
        state = ctx._priority_state
        assert state.priority_map["f.feature:5"] == 2

    def test_setup_mixed_rule_and_standalone_scenarios(self) -> None:
        standalone = FakeScenario("standalone", tags=["priority(5)"], filename="f.feature", line=3)
        rule_s = FakeScenario("rule_s", tags=["priority(1)"], filename="f.feature", line=8)
        rule = FakeRule("R", run_items=[rule_s], scenarios=[rule_s])
        feature = FakeFeature(
            "F", "f.feature",
            run_items=[standalone, rule],
            scenarios=[standalone, rule_s],
        )
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, order=True)
        state = ctx._priority_state
        assert state.priority_map["f.feature:3"] == 5
        assert state.priority_map["f.feature:8"] == 1

    def test_setup_rule_with_no_run_items(self) -> None:
        rule = FakeRule("R", run_items=None, scenarios=[])
        feature = FakeFeature("F", "f.feature", run_items=[rule], scenarios=[])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, order=True)
        state = ctx._priority_state
        assert len(state.priority_map) == 0

    def test_setup_populates_rule_tag_map(self) -> None:
        s1 = FakeScenario("s1", filename="f.feature", line=5)
        rule = FakeRule("R", tags=["critical", "priority(2)"], run_items=[s1], scenarios=[s1])
        feature = FakeFeature("F", "f.feature", run_items=[rule], scenarios=[s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, order=True)
        state = ctx._priority_state
        assert state.rule_tag_map["f.feature:5"] == ["critical", "priority(2)"]

    def test_is_critical_considers_rule_tags(self) -> None:
        s1 = FakeScenario("s1", filename="f.feature", line=5)
        rule = FakeRule("R", tags=["critical"], run_items=[s1], scenarios=[s1])
        feature = FakeFeature("F", "f.feature", run_items=[rule], scenarios=[s1])
        runner = FakeRunner(features=[feature])
        ctx = FakeContext(_runner=runner)
        setup_priority(ctx, order=True)
        state = ctx._priority_state
        s1.status = "failed"
        after_scenario_hook(ctx, s1)
        assert state.report._entries[0].is_critical is True

    def test_executed_count_excludes_skipped(self) -> None:
        state = make_state()
        ctx = FakeContext(_priority_state=state)
        s1 = FakeScenario("s1", status="passed")
        s2 = FakeScenario("s2", status="skipped")
        after_scenario_hook(ctx, s1)
        after_scenario_hook(ctx, s2)
        assert state.executed_count == 1
