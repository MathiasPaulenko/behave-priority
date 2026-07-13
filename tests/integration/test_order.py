"""Integration tests for priority ordering."""

from __future__ import annotations

ENV = """\
from behave_priority import setup_priority, before_scenario_hook, after_scenario_hook

def before_all(context):
    setup_priority(context, order=True)

def before_scenario(context, scenario):
    before_scenario_hook(context, scenario)

def after_scenario(context, scenario):
    after_scenario_hook(context, scenario)
"""

FEATURE = """\
Feature: Order test

  @priority(3)
  Scenario: Low
    Given a passing step

  @priority(1)
  Scenario: High
    Given a passing step

  @priority(2)
  Scenario: Medium
    Given a passing step
"""


def test_priority_order(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert result.scenario_names == ["High", "Medium", "Low"]


def test_all_scenarios_pass(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert len(result.passed_scenarios) == 3
    assert len(result.failed_scenarios) == 0


def test_returncode_zero_on_all_pass(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert result.returncode == 0
