"""Integration test fixtures for running behave."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest


def _infer_status(step_statuses: list[str]) -> str:
    """Infer scenario status from step statuses."""
    if not step_statuses:
        return "skipped"
    if any(s == "failed" for s in step_statuses):
        return "failed"
    if all(s == "passed" for s in step_statuses):
        return "passed"
    if any(s == "undefined" for s in step_statuses):
        return "undefined"
    return "skipped"


@dataclass
class BehaveResult:
    """Result of running behave."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def scenario_lines(self) -> list[tuple[str, str]]:
        """Parse (scenario_name, status) from plain format output.

        In plain format, each scenario block starts with '  Scenario: Name'
        and steps show '... passed/failed/skipped'. We infer scenario status
        from its steps.
        """
        results: list[tuple[str, str]] = []
        current_name: str | None = None
        step_statuses: list[str] = []

        for line in self.stdout.splitlines():
            sc_match = re.match(r"\s+Scenario:\s+(.+)", line)
            if sc_match:
                if current_name is not None:
                    status = _infer_status(step_statuses)
                    results.append((current_name, status))
                current_name = sc_match.group(1).strip()
                step_statuses = []
                continue

            step_match = re.match(
                r"\s+(?:Given|When|Then|And|But)\s+.+\.\.\.\s+(\w+)", line
            )
            if step_match and current_name is not None:
                step_statuses.append(step_match.group(1))

        if current_name is not None:
            status = _infer_status(step_statuses)
            results.append((current_name, status))

        return results

    @property
    def scenario_names(self) -> list[str]:
        return [name for name, _ in self.scenario_lines]

    @property
    def passed_scenarios(self) -> list[str]:
        return [name for name, status in self.scenario_lines if status == "passed"]

    @property
    def failed_scenarios(self) -> list[str]:
        return [name for name, status in self.scenario_lines if status == "failed"]

    @property
    def skipped_scenarios(self) -> list[str]:
        return [name for name, status in self.scenario_lines if status == "skipped"]


DEFAULT_STEPS = """\
from behave import given, then

@given('a passing step')
def step_pass(context):
    pass

@given('a failing step')
def step_fail(context):
    assert False, "Intentional failure"

@then('it passes')
def step_then_pass(context):
    pass

@then('it fails')
def step_then_fail(context):
    assert False, "Intentional failure"
"""


@pytest.fixture
def run_behave(tmp_path: Path) -> Callable[..., BehaveResult]:
    """Fixture to run behave on dynamically created features."""

    def _run(
        env_py: str,
        feature_content: str,
        steps_py: str = "",
        feature_filename: str = "test.feature",
    ) -> BehaveResult:
        features_dir = tmp_path / "features"
        features_dir.mkdir(exist_ok=True)
        (features_dir / "environment.py").write_text(env_py)
        (features_dir / feature_filename).write_text(feature_content)
        steps_dir = features_dir / "steps"
        steps_dir.mkdir(exist_ok=True)
        (steps_dir / "steps.py").write_text(steps_py or DEFAULT_STEPS)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "behave",
                "--no-color",
                "--no-capture",
                "--format",
                "plain",
                str(features_dir),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return BehaveResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    return _run
