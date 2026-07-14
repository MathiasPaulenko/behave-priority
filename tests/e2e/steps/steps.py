"""Step definitions for E2E behave-priority tests."""

from behave import given, then, when


@given("a step that passes")
def step_passes(context):
    pass


@given("a step that fails")
def step_fails(context):
    raise AssertionError("Intentional failure for testing")


@given("a step that is undefined")
def step_undefined(context):
    pass  # This will be undefined if not registered


@when("the scenario runs")
def when_runs(context):
    pass


@then("the scenario should complete")
def then_completes(context):
    pass
