"""Integration tests without setup_priority — behave runs normally."""

from __future__ import annotations

ENV = """\
def before_scenario(context, scenario):
    pass

def after_scenario(context, scenario):
    pass
"""

FEATURE = """\
Feature: No config test

  Scenario: Second defined
    Given a passing step

  Scenario: First defined
    Given a passing step
"""


def test_behave_runs_normally(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert result.returncode == 0


def test_preserves_definition_order(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert result.scenario_names == ["Second defined", "First defined"]


def test_all_scenarios_pass(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert len(result.passed_scenarios) == 2


def test_no_priority_report_in_output(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert "Priority Execution Report" not in result.stdout
