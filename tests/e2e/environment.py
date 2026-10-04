"""Behave environment for E2E tests.

Reads the ``BEHAVE_PRIORITY_CONFIG`` environment variable to select
which setup_priority configuration to use. This allows different test
suites to exercise different features of behave-priority.

Supported values:
    - ``order``: order=True, report=True
    - ``failfast``: order=True, stop_after_failures=1, report=True
    - ``critical``: order=True, stop_on_critical=True, report=True
    - ``smoke``: order=True, priority_tag="smoke", report=True
    - ``outline``: order=True, report=True
    - ``rule``: order=True, report=True
    - ``feature_priority``: order=True, report=True
    - ``none``: no setup_priority call (hooks are no-ops)
"""

from __future__ import annotations

import os

from behave_priority import (
    after_scenario_hook,
    before_scenario_hook,
    priority_report,
    setup_priority,
)


def before_all(context):
    config_name = os.environ.get("BEHAVE_PRIORITY_CONFIG", "order")
    if config_name == "none":
        return
    kwargs = {
        "order": True,
        "report": True,
    }
    if config_name == "failfast":
        kwargs["stop_after_failures"] = 1
    elif config_name == "critical":
        kwargs["stop_on_critical"] = True
    elif config_name == "smoke":
        kwargs["priority_tag"] = "smoke"
    setup_priority(context, **kwargs)


def before_scenario(context, scenario):
    before_scenario_hook(context, scenario)


def after_scenario(context, scenario):
    after_scenario_hook(context, scenario)


def after_all(context):
    priority_report(context)
