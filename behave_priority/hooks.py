"""Behave hooks for priority execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from behave_priority.config import PriorityConfig, ReportFormat
from behave_priority.parallel import (
    ParallelCoordinator,
    cleanup_coordinator,
    create_coordinator,
)
from behave_priority.parser import is_critical, resolve_priority
from behave_priority.report import PriorityReport
from behave_priority.sorter import ScenarioSorter

logger = logging.getLogger(__name__)


def _scenario_key(scenario: Any) -> str:
    """Build a deterministic key for a scenario.

    Uses ``filename`` and ``line`` attributes when available (as behave
    provides), falling back to ``id()`` for objects without them.

    Args:
        scenario: The scenario object.

    Returns:
        A string key unique to the scenario.
    """
    filename = getattr(scenario, "filename", None)
    line = getattr(scenario, "line", None)
    if filename is not None and line is not None:
        return f"{filename}:{line}"
    name = getattr(scenario, "name", "")
    return f"id:{id(scenario)}:{name}"


def _map_scenario(
    state: PriorityState,
    scenario: Any,
    feature_tags: list[str],
    feature_name: str,
    config: PriorityConfig,
    rule_tags: list[str] | None = None,
) -> None:
    """Map a scenario and its expanded examples into priority state.

    Handles both plain scenarios and ScenarioOutline objects. For
    ScenarioOutline, each expanded example is mapped individually so
    that ``after_scenario_hook`` can resolve the correct priority.

    Args:
        state: The priority state to populate.
        scenario: The scenario or scenario outline to map.
        feature_tags: Tags from the parent feature.
        feature_name: Name or filename of the parent feature.
        config: The priority configuration.
        rule_tags: Tags from the parent rule (Gherkin v6), if any.
    """
    effective_rule_tags = rule_tags or []

    expanded = getattr(scenario, "scenarios", None)
    if expanded:
        for example in expanded:
            key = _scenario_key(example)
            state.priority_map[key] = resolve_priority(
                example.tags, feature_tags, config, effective_rule_tags
            )
            state.feature_map[key] = feature_name
            state.rule_tag_map[key] = effective_rule_tags
            state.feature_tag_map[key] = feature_tags
    else:
        key = _scenario_key(scenario)
        state.priority_map[key] = resolve_priority(
            scenario.tags, feature_tags, config, effective_rule_tags
        )
        state.feature_map[key] = feature_name
        state.rule_tag_map[key] = effective_rule_tags
        state.feature_tag_map[key] = feature_tags


@dataclass
class PriorityState:
    """Mutable execution state, persisted across hooks via context.

    .. note::
        This state is **not shared across processes**. When behave runs with
        ``--parallel``, each worker process gets its own isolated
        ``PriorityState``. However, when ``parallel_coord=True`` and
        ``BEHAVE_PRIORITY_COORD_DIR`` is set, a :class:`ParallelCoordinator`
        shares fail-fast state across workers via file-based IPC.

    Attributes:
        config: The priority configuration.
        report: The execution report collector.
        sorter: The scenario sorter instance.
        coordinator: Optional parallel coordinator for cross-process
            fail-fast. None when ``parallel_coord`` is disabled.
        failed_count: Number of failed scenarios so far.
        critical_failed: Whether any critical scenario has failed.
        should_stop: Whether fail-fast conditions have been triggered.
        executed_count: Number of scenarios actually executed.
        skipped_count: Number of scenarios skipped by fail-fast.
        priority_map: Maps scenario key to resolved priority.
        feature_map: Maps scenario key to parent feature name.
        rule_tag_map: Maps scenario key to parent rule tags (Gherkin v6).
        feature_tag_map: Maps scenario key to parent feature tags.
    """

    config: PriorityConfig
    report: PriorityReport
    sorter: ScenarioSorter
    coordinator: ParallelCoordinator | None = None
    failed_count: int = 0
    critical_failed: bool = False
    should_stop: bool = False
    executed_count: int = 0
    skipped_count: int = 0
    priority_map: dict[str, int] = field(default_factory=dict)
    feature_map: dict[str, str] = field(default_factory=dict)
    rule_tag_map: dict[str, list[str]] = field(default_factory=dict)
    feature_tag_map: dict[str, list[str]] = field(default_factory=dict)

    def check_fail_fast(self) -> bool:
        """Check if fail-fast conditions are met.

        When a parallel coordinator is active, global failure counts
        across all workers are considered in addition to local state.

        Returns:
            True if execution should stop after the current scenario.
        """
        if self.coordinator is not None:
            return self.coordinator.should_stop(
                stop_after_failures=self.config.stop_after_failures,
                stop_on_critical=self.config.stop_on_critical,
            )

        if (
            self.config.stop_after_failures is not None
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
    report_format: ReportFormat = "text",
    parallel_coord: bool = False,
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
        report_format: Output format for the report (``"text"``, ``"json"``, ``"csv"``).
        parallel_coord: Enable cross-process fail-fast coordination.
            Requires ``BEHAVE_PRIORITY_COORD_DIR`` env var to be set.
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
        report_format=report_format,
        parallel_coord=parallel_coord,
    )

    runner = getattr(context, "_runner", None)
    if runner is None:
        runner = getattr(context, "runner", None)
    if runner is None:
        logger.warning(
            "cannot access behave's runner. "
            "Scenarios will NOT be reordered and priority hooks "
            "will have no effect. Ensure this is called from "
            "before_all() in environment.py."
        )
        return

    features = getattr(runner, "features", None)
    if features is None:
        features = getattr(runner, "feature_list", None)
    if features is None:
        logger.warning(
            "runner has no 'features' or 'feature_list' "
            "attribute. Scenarios will NOT be reordered."
        )
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
        feature_name = feature.name or feature.filename
        items = getattr(feature, "run_items", None) or feature.scenarios
        for item in items:
            if hasattr(item, "run_items"):
                rule_tags: list[str] = getattr(item, "tags", [])
                inner_items: Any = (
                    getattr(item, "run_items", None)
                    or getattr(item, "scenarios", [])
                )
                for scenario in inner_items:
                    _map_scenario(
                        state, scenario, feature.tags, feature_name, config, rule_tags
                    )
            else:
                _map_scenario(
                    state, item, feature.tags, feature_name, config
                )

    context._priority_state = state

    if config.parallel_coord:
        coordinator = create_coordinator()
        if coordinator is not None:
            state.coordinator = coordinator
            context._priority_coordinator = coordinator
        else:
            logger.warning(
                "parallel_coord=True but BEHAVE_PRIORITY_COORD_DIR "
                "env var is not set. Cross-process coordination "
                "will not be active."
            )


def before_scenario_hook(context: Any, scenario: Any) -> None:
    """Skip scenario if fail-fast has been triggered.

    Intended for use as ``before_scenario`` in behave's ``environment.py``.
    Recording of skipped scenarios is handled by ``after_scenario_hook``
    to avoid duplicate entries.

    Args:
        context: Behave's context object.
        scenario: The scenario about to run.
    """
    state: PriorityState | None = getattr(context, "_priority_state", None)
    if state is None:
        return

    if state.coordinator is not None and not state.should_stop:
        state.should_stop = state.check_fail_fast()

    if state.should_stop:
        state.skipped_count += 1
        if hasattr(scenario, "skip"):
            scenario.skip("fail-fast triggered")


def after_scenario_hook(context: Any, scenario: Any) -> None:
    """Record scenario result and update fail-fast state.

    Intended for use as ``after_scenario`` in behave's ``environment.py``.
    Both executed and skipped scenarios are recorded here to avoid
    duplicate entries.

    Args:
        context: Behave's context object.
        scenario: The scenario that just finished.
    """
    state: PriorityState | None = getattr(context, "_priority_state", None)
    if state is None:
        return

    key = _scenario_key(scenario)
    priority = state.priority_map.get(key, state.config.default_priority)
    raw_status = getattr(scenario, "status", "unknown")
    status = raw_status.name if hasattr(raw_status, "name") else str(raw_status)
    duration = getattr(scenario, "duration", 0.0)
    feature_name = state.feature_map.get(key, "")

    rule_tags = state.rule_tag_map.get(key, [])
    feature_tags = state.feature_tag_map.get(key, [])
    scenario_tags = getattr(scenario, "tags", [])
    combined_tags = list(scenario_tags) + rule_tags + feature_tags
    is_crit = is_critical(combined_tags, state.config.critical_tag)

    state.report.record(
        scenario_name=getattr(scenario, "name", "unknown"),
        feature_name=feature_name,
        priority=priority,
        status=status,
        duration=duration,
        is_critical=is_crit,
    )

    if status == "skipped":
        state.should_stop = state.check_fail_fast()
        return

    state.executed_count += 1

    if status == "failed":
        state.failed_count += 1
        if is_crit:
            state.critical_failed = True
        if state.coordinator is not None:
            state.coordinator.report_failure(is_critical=is_crit)

    state.should_stop = state.check_fail_fast()


def get_report(context: Any) -> PriorityReport | None:
    """Retrieve the priority execution report from context.

    Allows programmatic access to the ``PriorityReport`` object after a run,
    without accessing the private ``context._priority_state``.

    Args:
        context: Behave's context object.

    Returns:
        The ``PriorityReport`` if priority state was set up, otherwise None.
    """
    state: PriorityState | None = getattr(context, "_priority_state", None)
    if state is None:
        return None
    return state.report


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
        fmt = state.config.report_format
        if fmt == "json":
            logger.info("\n%s", state.report.to_json())
        elif fmt == "csv":
            logger.info("\n%s", state.report.to_csv())
        else:
            logger.info("\n%s", state.report.render())


def cleanup_parallel_coord(context: Any) -> None:
    """Clean up the parallel coordinator for this worker.

    Intended for use in ``after_all`` alongside ``priority_report``.
    Removes this worker's file from the coordination directory.

    Args:
        context: Behave's context object.
    """
    cleanup_coordinator(context)
