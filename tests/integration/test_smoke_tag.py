"""Integration tests for priority_tag (smoke) grouping."""

from __future__ import annotations

ENV = """\
from behave_priority import setup_priority, before_scenario_hook, after_scenario_hook

def before_all(context):
    setup_priority(context, priority_tag="smoke")

def before_scenario(context, scenario):
    before_scenario_hook(context, scenario)

def after_scenario(context, scenario):
    after_scenario_hook(context, scenario)
"""

FEATURE = """\
Feature: Smoke tag test

  @smoke
  @priority(5)
  Scenario: Smoke A
    Given a passing step

  @priority(1)
  Scenario: Normal A
    Given a passing step

  @smoke
  @priority(10)
  Scenario: Smoke B
    Given a passing step

  @priority(2)
  Scenario: Normal B
    Given a passing step
"""


def test_smoke_scenarios_run_first(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    names = result.scenario_names
    smoke_indices = [i for i, n in enumerate(names) if "Smoke" in n]
    normal_indices = [i for i, n in enumerate(names) if "Normal" in n]
    assert max(smoke_indices) < min(normal_indices)


def test_all_scenarios_pass(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert len(result.passed_scenarios) == 4


def test_smoke_order_within_group(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    names = result.scenario_names
    smoke_names = [n for n in names if "Smoke" in n]
    assert smoke_names == ["Smoke A", "Smoke B"]


def test_normal_order_within_group(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    names = result.scenario_names
    normal_names = [n for n in names if "Normal" in n]
    assert normal_names == ["Normal A", "Normal B"]
