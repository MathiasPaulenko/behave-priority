"""Behave hooks for priority execution."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

from behave_priority.config import PriorityConfig
from behave_priority.parser import is_critical, resolve_priority
from behave_priority.report import PriorityReport
from behave_priority.sorter import ScenarioSorter


@dataclass
class PriorityState:
    """Mutable execution state, persisted across hooks via context.

    Attributes:
        config: The priority configuration.
        report: The execution report collector.
        sorter: The scenario sorter instance.
        failed_count: Number of failed scenarios so far.
        critical_failed: Whether any critical scenario has failed.
        should_stop: Whether fail-fast conditions have been triggered.
        executed_count: Number of scenarios executed.
        skipped_count: Number of scenarios skipped by fail-fast.
        priority_map: Maps scenario ``id()`` to resolved priority.
    """

    config: PriorityConfig
    report: PriorityReport
    sorter: ScenarioSorter
    failed_count: int = 0
    critical_failed: bool = False
    should_stop: bool = False
    executed_count: int = 0
    skipped_count: int = 0
    priority_map: dict[int, int] = field(default_factory=dict)

    def check_fail_fast(self) -> bool:
        """Check if fail-fast conditions are met.

        Returns:
            True if execution should stop after the current scenario.
        """
        if (
            self.config.stop_after_failures is not None
            and self.config.stop_after_failures > 0
            and self.failed_count >= self.config.stop_after_failures
        ):
            return True

        return self.config.stop_on_critical and self.critical_failed


def setup_priority(
    context: Any,
    *,
    order: bool = False,
    reverse: bool = False,
    priority_tag: str | None = None,
    stop_after_failures: int | None = None,
    stop_on_critical: bool = False,
    critical_tag: str = "critical",
    default_priority: int = 999,
    report: bool = False,
) -> None:
    """Set up priority execution in before_all hook.

    All configuration is passed explicitly — no CLI flags.

    Args:
        context: Behave's context object (``context`` in ``before_all``).
        order: Sort scenarios by priority (highest first).
        reverse: Reverse sort order (lowest priority first).
        priority_tag: Tag name to run first (e.g. ``"smoke"``).
        stop_after_failures: Stop after N failed scenarios.
        stop_on_critical: Stop if any critical scenario fails.
        critical_tag: Tag name that marks a scenario as critical.
        default_priority: Priority for scenarios without a priority tag.
        report: Print execution report after run.
    """
    config = PriorityConfig(
        order=order,
        reverse=reverse,
        priority_tag=priority_tag,
        stop_after_failures=stop_after_failures,
        stop_on_critical=stop_on_critical,
        critical_tag=critical_tag,
        default_priority=default_priority,
        report=report,
    )

    runner = getattr(context, "_runner", None)
    if runner is None:
        runner = getattr(context, "runner", None)
    if runner is None:
        warnings.warn(
            "behave-priority: cannot access runner. "
            "Scenarios will not be reordered.",
            RuntimeWarning,
            stacklevel=2,
        )
        return

    features = getattr(runner, "features", None)
    if features is None:
        features = getattr(runner, "feature_list", None)
    if features is None:
        return

    sorter = ScenarioSorter(config)
    sorted_features = sorter.sort(features)
    features[:] = sorted_features

    priority_report_obj = PriorityReport(config)
    state = PriorityState(
        config=config,
        report=priority_report_obj,
        sorter=sorter,
    )

    for feature in sorted_features:
        items = getattr(feature, "run_items", None) or feature.scenarios
        for scenario in items:
            scenario_id = id(scenario)
            state.priority_map[scenario_id] = resolve_priority(
                scenario.tags, feature.tags, config
            )

    context._priority_state = state


def before_scenario_hook(context: Any, scenario: Any) -> None:
    """Skip scenario if fail-fast has been triggered.

    Intended for use as ``before_scenario`` in behave's ``environment.py``.

    Args:
        context: Behave's context object.
        scenario: The scenario about to run.
    """
    state: PriorityState | None = getattr(context, "_priority_state", None)
    if state is None:
        return

    if state.should_stop:
        state.skipped_count += 1
        if hasattr(scenario, "skip"):
            scenario.skip("fail-fast triggered")


def after_scenario_hook(context: Any, scenario: Any) -> None:
    """Record scenario result and update fail-fast state.

    Intended for use as ``after_scenario`` in behave's ``environment.py``.

    Args:
        context: Behave's context object.
        scenario: The scenario that just finished.
    """
    state: PriorityState | None = getattr(context, "_priority_state", None)
    if state is None:
        return

    scenario_id = id(scenario)
    priority = state.priority_map.get(scenario_id, state.config.default_priority)
    status = getattr(scenario, "status", "unknown")
    duration = getattr(scenario, "duration", 0.0)

    feature_name = ""
    runner = getattr(context, "_runner", None)
    if runner is not None:
        for feature in getattr(runner, "features", []):
            items = getattr(feature, "run_items", None) or feature.scenarios
            if scenario in items:
                feature_name = feature.name or feature.filename
                break

    is_crit = is_critical(scenario.tags, state.config.critical_tag)

    state.report.record(
        scenario_name=getattr(scenario, "name", "unknown"),
        feature_name=feature_name,
        priority=priority,
        status=status,
        duration=duration,
        is_critical=is_crit,
    )

    state.executed_count += 1

    if status == "failed":
        state.failed_count += 1
        if is_crit:
            state.critical_failed = True

    state.should_stop = state.check_fail_fast()


def priority_report(context: Any) -> None:
    """Print the priority execution report.

    Intended for use as ``after_all`` in behave's ``environment.py``.

    Args:
        context: Behave's context object.
    """
    state: PriorityState | None = getattr(context, "_priority_state", None)
    if state is None:
        return

    if state.config.report:
        print(state.report.render())
