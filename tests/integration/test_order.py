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


FEATURE_A = """\
Feature: Feature A

  @priority(2)
  Scenario: Auth login
    Given a passing step

  @priority(5)
  Scenario: Auth logout
    Given a passing step
"""

FEATURE_B = """\
Feature: Feature B

  @priority(1)
  Scenario: Payment checkout
    Given a passing step

  @priority(3)
  Scenario: Payment refund
    Given a passing step
"""


def test_multiple_features_ordered_by_best_scenario(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE_A,
        extra_features={"feature_b.feature": FEATURE_B},
    )
    names = result.scenario_names
    assert names == [
        "Payment checkout",
        "Payment refund",
        "Auth login",
        "Auth logout",
    ]


def test_multiple_features_all_pass(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE_A,
        extra_features={"feature_b.feature": FEATURE_B},
    )
    assert len(result.passed_scenarios) == 4
    assert len(result.failed_scenarios) == 0
