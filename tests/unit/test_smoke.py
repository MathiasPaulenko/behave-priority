"""Smoke test: package imports correctly."""

import behave_priority


def test_version() -> None:
    assert behave_priority.__version__ == "1.0.0"


def test_all_exports() -> None:
    expected = {
        "PriorityConfig",
        "ReportFormat",
        "parse_priority",
        "parse_feature_priority",
        "resolve_priority",
        "is_critical",
        "ScenarioSorter",
        "setup_priority",
        "before_scenario_hook",
        "after_scenario_hook",
        "get_report",
        "priority_report",
        "cleanup_parallel_coord",
        "ParallelCoordinator",
        "cleanup_coordinator",
        "create_coordinator",
        "PriorityReport",
        "ReportEntry",
        "ReportSummary",
        "PriorityError",
        "PriorityParseError",
        "__version__",
    }
    assert set(behave_priority.__all__) == expected


def test_imports_resolved() -> None:
    for name in behave_priority.__all__:
        assert hasattr(behave_priority, name), f"Missing export: {name}"
