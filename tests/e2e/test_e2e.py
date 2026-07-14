"""E2E tests that run behave with real .feature files.

These tests exercise behave-priority against actual behave execution,
verifying scenario ordering, fail-fast behavior, critical tag handling,
smoke tag priority, scenario outlines, and Gherkin v6 Rule support.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

FEATURES_DIR = Path(__file__).parent / "features"


def run_behave(
    feature_file: str,
    config_name: str,
    *,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run behave against a single feature file with a priority config.

    Args:
        feature_file: Name of the .feature file inside FEATURES_DIR.
        config_name: Value for BEHAVE_PRIORITY_CONFIG env var.
        extra_args: Additional behave CLI arguments.

    Returns:
        The completed process with stdout, stderr, and return code.
    """
    env = os.environ.copy()
    env["BEHAVE_PRIORITY_CONFIG"] = config_name
    env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)

    cmd = [
        sys.executable, "-m", "behave",
        "--no-color",
        "--no-capture",
        "--format", "plain",
        str(FEATURES_DIR / feature_file),
    ]
    if extra_args:
        cmd.extend(extra_args)

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(FEATURES_DIR.parent),
        timeout=30,
    )


def extract_scenario_order(output: str) -> list[str]:
    """Extract scenario names in execution order from behave plain output.

    Args:
        output: Behave plain format stdout.

    Returns:
        List of scenario names in the order they appear.
    """
    scenarios: list[str] = []
    for line in output.splitlines():
        match = re.match(
            r"^(?:  ){1,2}Scenario(?: Outline)?: (.+)$", line
        )
        if match:
            scenarios.append(match.group(1).strip())
    return scenarios


def extract_statuses(output: str) -> dict[str, str]:
    """Extract scenario name to status mapping from behave output.

    Parses plain format lines (with ``... status``) for executed scenarios.
    For skipped scenarios, checks the Priority Execution Report table.

    Args:
        output: Behave plain format stdout.

    Returns:
        Dict mapping scenario name to status string.
    """
    statuses: dict[str, str] = {}
    current_scenario: str | None = None
    for line in output.splitlines():
        match = re.match(
            r"^(?:  ){1,2}Scenario(?: Outline)?: (.+)$", line
        )
        if match:
            current_scenario = match.group(1).strip()
            continue
        if current_scenario and "..." in line:
            status_match = re.search(r"\.\.\.\s*(\w+)", line)
            if status_match:
                statuses[current_scenario] = status_match.group(1)

    for line in output.splitlines():
        for name in list(statuses):
            if name in line:
                for status in ("skipped", "undefined"):
                    if line.strip().endswith(status):
                        if statuses.get(name, "") not in ("passed", "failed"):
                            statuses[name] = status

    return statuses


class TestPriorityOrdering:
    """Verify that scenarios are ordered by priority (lowest number first)."""

    def test_scenarios_ordered_by_priority(self) -> None:
        result = run_behave("priority_order.feature", "order")
        assert result.returncode == 0, result.stderr
        order = extract_scenario_order(result.stdout)
        assert len(order) == 4, f"Expected 4 scenarios, got {len(order)}: {order}"
        assert order[0] == "High priority scenario"
        assert order[1] == "Low priority scenario"
        assert order[2] == "Medium priority scenario"
        assert order[3] == "No priority tag scenario"

    def test_report_is_printed(self) -> None:
        result = run_behave("priority_order.feature", "order")
        assert "Priority Execution Report" in result.stdout
        assert "Summary:" in result.stdout

    def test_feature_priority_inherited(self) -> None:
        result = run_behave("feature_priority.feature", "feature_priority")
        assert result.returncode == 0, result.stderr
        order = extract_scenario_order(result.stdout)
        assert len(order) == 2
        assert order[0] == "Scenario with explicit priority overrides feature"
        assert order[1] == "Scenario without priority tag inherits feature priority"


class TestFailFast:
    """Verify fail-fast stops execution after N failures."""

    def test_stops_after_one_failure(self) -> None:
        result = run_behave("failfast.feature", "failfast")
        output = result.stdout + result.stderr
        assert "First scenario passes" in output
        assert "passed" in output
        assert "Second scenario fails" in output
        assert "failed" in output
        assert "Third scenario should be skipped" in output
        assert "skipped" in output
        assert "Fourth scenario should be skipped" in output

    def test_report_shows_skipped(self) -> None:
        result = run_behave("failfast.feature", "failfast")
        assert "skipped" in result.stdout
        assert "Time saved" in result.stdout


class TestCriticalStop:
    """Verify stop_on_critical halts after critical scenario fails."""

    def test_critical_failure_stops_execution(self) -> None:
        result = run_behave("critical.feature", "critical")
        output = result.stdout + result.stderr
        assert "Critical scenario passes" in output
        assert "Critical scenario fails" in output
        assert "Non-critical scenario after critical failure" in output
        assert "skipped" in output

    def test_report_shows_critical_section(self) -> None:
        result = run_behave("critical.feature", "critical")
        assert "Critical:" in result.stdout


class TestSmokeTag:
    """Verify priority_tag brings tagged scenarios first."""

    def test_smoke_scenarios_run_first(self) -> None:
        result = run_behave("smoke_tag.feature", "smoke")
        assert result.returncode == 0, result.stderr
        order = extract_scenario_order(result.stdout)
        assert len(order) == 3
        assert order[0] == "Smoke tagged scenario"


class TestScenarioOutline:
    """Verify scenario outlines are handled correctly."""

    def test_outline_examples_executed(self) -> None:
        result = run_behave("outline.feature", "outline")
        assert result.returncode == 0, result.stderr
        order = extract_scenario_order(result.stdout)
        assert len(order) == 4
        outline_names = [n for n in order if "Outline scenario" in n]
        assert len(outline_names) == 3
        assert order[-1] == "Scenario after outline"

    def test_outline_examples_have_priority(self) -> None:
        result = run_behave("outline.feature", "outline")
        assert "Priority Execution Report" in result.stdout
        assert "priority" in result.stdout.lower()


class TestRuleSupport:
    """Verify Gherkin v6 Rule objects are sorted correctly."""

    def test_rule_scenarios_ordered(self) -> None:
        result = run_behave("rule_priority.feature", "rule")
        assert result.returncode == 0, result.stderr
        order = extract_scenario_order(result.stdout)
        assert len(order) == 3
        assert order[0] == "Rule scenario with high priority"
        assert order[1] == "Standalone scenario before rule"
        assert order[2] == "Rule scenario with low priority"


class TestNoConfig:
    """Verify behave runs without priority setup (graceful degradation)."""

    def test_behave_without_priority_config(self) -> None:
        env = os.environ.copy()
        env.pop("BEHAVE_PRIORITY_CONFIG", None)
        env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)
        result = subprocess.run(
            [
                sys.executable, "-m", "behave",
                "--no-color",
                "--no-capture",
                "--format", "plain",
                str(FEATURES_DIR / "priority_order.feature"),
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(FEATURES_DIR.parent),
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
