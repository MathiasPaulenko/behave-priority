"""Integration tests for report output."""

from __future__ import annotations

ENV = """\
from behave_priority import (
    setup_priority,
    before_scenario_hook,
    after_scenario_hook,
    priority_report,
)

def before_all(context):
    setup_priority(context, order=True, report=True)

def before_scenario(context, scenario):
    before_scenario_hook(context, scenario)

def after_scenario(context, scenario):
    after_scenario_hook(context, scenario)

def after_all(context):
    priority_report(context)
"""

FEATURE = """\
Feature: Report test

  @priority(1)
  Scenario: Alpha
    Given a passing step

  @priority(2)
  Scenario: Beta
    Given a passing step

  @priority(3)
  Scenario: Gamma
    Given a passing step
"""


def test_report_header_in_output(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert "Priority Execution Report" in result.stdout


def test_report_contains_scenario_names(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert "Alpha" in result.stdout
    assert "Beta" in result.stdout
    assert "Gamma" in result.stdout


def test_report_contains_summary(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert "Summary:" in result.stdout
    assert "3 passed" in result.stdout


def test_report_no_critical_section(run_behave: object) -> None:
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=FEATURE,
    )
    assert "Critical:" not in result.stdout


def test_report_with_failure(run_behave: object) -> None:
    feature = """\
Feature: Report with failure

  @priority(1)
  Scenario: Passes
    Given a passing step

  @priority(2)
  Scenario: Fails
    Given a failing step
"""
    result = run_behave(  # type: ignore[operator]
        env_py=ENV,
        feature_content=feature,
    )
    assert "1 failed" in result.stdout
    assert "1 passed" in result.stdout
