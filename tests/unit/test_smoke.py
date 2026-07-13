"""Smoke test: package imports correctly."""

import behave_priority


def test_version() -> None:
    assert behave_priority.__version__ == "0.1.0"


def test_all_exports() -> None:
    expected = {
        "PriorityConfig",
        "PriorityQueue",
        "parse_priority",
        "parse_feature_priority",
        "resolve_priority",
        "is_critical",
        "ScenarioSorter",
        "setup_priority",
        "before_scenario_hook",
        "after_scenario_hook",
        "priority_report",
        "PriorityReport",
        "ReportEntry",
        "ReportSummary",
        "PriorityError",
        "PriorityParseError",
        "StopExecutionError",
        "__version__",
    }
    assert set(behave_priority.__all__) == expected


def test_imports_resolved() -> None:
    for name in behave_priority.__all__:
        assert hasattr(behave_priority, name), f"Missing export: {name}"
