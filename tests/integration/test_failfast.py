"""Integration tests for fail-fast behavior."""

from __future__ import annotations

ENV = """\
from behave_priority import setup_priority, before_scenario_hook, after_scenario_hook

def before_all(context):
    setup_priority(context, order=True, stop_after_failures=2)

def before_scenario(context, scenario):
    before_scenario_hook(context, scenario)

def after_scenario(context, scenario):
    after_scenario_hook(context, scenario)
"""

FEATURE = """\
Feature: Fail-fast test

  @priority(1)
  Scenario: First fail
    Given a failing step

  @priority(2)
  Scenario: Second fail
    Given a failing step

  @priority(3)
  Scenario: Third pass
    Given a passing step

  @priority(4)
  Scenario: Fourth pass
    Given a passing step

  @priority(5)
  Scenario: Fifth pass
    Given a passing step
"""


def test_stops_after_2_failures(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert len(result.failed_scenarios) == 2


def test_skips_remaining_scenarios(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert len(result.skipped_scenarios) == 3
    assert "Third pass" in result.skipped_scenarios
    assert "Fourth pass" in result.skipped_scenarios
    assert "Fifth pass" in result.skipped_scenarios


def test_failed_scenarios_in_order(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert result.failed_scenarios == ["First fail", "Second fail"]


def test_returncode_nonzero_on_failures(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert result.returncode != 0


def test_no_passed_scenarios(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert len(result.passed_scenarios) == 0
