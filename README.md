# behave-priority

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-390%20passed-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen.svg)]()
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue.svg)]()
[![ruff](https://img.shields.io/badge/ruff-passing-brightgreen.svg)]()

Priority-based execution for Behave BDD. Execute scenarios ordered by priority, with fail-fast and smoke-first support.

## Problem

Behave executes scenarios in file order. There is no way to:

- Run critical tests first
- Stop after N failures (intelligent fail-fast)
- Run smoke tests before regression
- Guarantee coverage when time is limited

In CI, if critical tests fail, you waste time waiting for the full regression suite to finish.

## Solution

`behave-priority` reorders scenario execution by priority tags and provides fail-fast controls — all configured programmatically in `environment.py`, no CLI flags needed.

## Features

### Priority tags

- `@priority(1)` tag on scenarios — lower number = higher priority
- `@feature-priority(1)` at feature level — applies to all scenarios in the feature
- Scenario-level `@priority(N)` overrides feature-level priority
- Scenarios without priority tag default to lowest priority (executed last)

### Execution ordering

- `order=True` — executes scenarios from highest to lowest priority
- `priority_tag="smoke"` — executes scenarios with that tag first, then the rest
- `reverse=True` — executes lowest priority first (useful for debugging)

### Fail-fast

- `stop_after_failures=N` — stops execution after N failed scenarios
- `stop_on_critical=True` — stops if any `@critical` scenario fails
- Combines with `order=True`: run critical first, stop if they fail, skip regression

### Parallel coordination

When running with `behave --parallel=N`, each worker is a separate process. By default, fail-fast is per-worker only. To coordinate fail-fast across all workers:

1. Set the `BEHAVE_PRIORITY_COORD_DIR` environment variable to a shared directory path
2. Pass `parallel_coord=True` to `setup_priority`

```bash
export BEHAVE_PRIORITY_COORD_DIR=/tmp/behave_priority_coord
behave --parallel=4
```

```python
setup_priority(
    context,
    order=True,
    stop_after_failures=3,
    parallel_coord=True,
)
```

Each worker writes its failure state to a JSON file in the coordination directory. `stop_after_failures` and `stop_on_critical` are evaluated globally across all workers. Call `cleanup_parallel_coord(context)` in `after_all` to remove the worker's file.

### Reporting

- `report=True` — prints execution order with priorities and timing
- `report_format="text"` (default) — human-readable table with summary
- `report_format="json"` — machine-readable JSON with entries and summary
- `report_format="csv"` — CSV with one row per scenario entry
- Shows: scenario name, priority value, status (passed/failed/skipped), duration
- Summary: how many critical passed, how many failed, total time saved by fail-fast
- `time_saved` estimation uses priority-bucketed averages (scenarios grouped by priority range 0-99, 100-199, etc.)

Example with JSON output for CI/CD integration:

```python
setup_priority(
    context,
    order=True,
    report=True,
    report_format="json",
)
```

## Installation

```bash
pip install behave-priority
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick start

In your `features/environment.py`:

```python
from behave_priority import (
    setup_priority,
    before_scenario_hook,
    after_scenario_hook,
    priority_report,
)

def before_all(context):
    setup_priority(
        context,
        order=True,
        stop_after_failures=3,
        stop_on_critical=True,
        report=True,
    )

def before_scenario(context, scenario):
    before_scenario_hook(context, scenario)

def after_scenario(context, scenario):
    after_scenario_hook(context, scenario)

def after_all(context):
    priority_report(context)
```

In your `.feature` files:

```gherkin
Feature: User authentication

  @priority(1)
  @critical
  Scenario: Login with valid credentials
    Given a registered user
    When the user logs in
    Then the user should be authenticated

  @priority(2)
  Scenario: Login with invalid password
    Given a registered user
    When the user logs in with wrong password
    Then the login should fail

  @priority(5)
  Scenario: Remember me checkbox
    Given a registered user
    When the user checks remember me
    Then the session should persist
```

## API reference

### `setup_priority(context, **kwargs)`

Configures priority execution in `before_all`. All parameters are optional.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `order` | `bool` | `False` | Sort scenarios by priority |
| `reverse` | `bool` | `False` | Reverse sort order (lowest priority first) |
| `priority_tag` | `str \| None` | `None` | Tag name to run first (e.g. `"smoke"`) |
| `stop_after_failures` | `int \| None` | `None` | Stop after N failures |
| `stop_on_critical` | `bool` | `False` | Stop if any `@critical` scenario fails |
| `critical_tag` | `str` | `"critical"` | Tag name for critical scenarios |
| `default_priority` | `int` | `999` | Priority for untagged scenarios |
| `report` | `bool` | `False` | Print execution report after run |
| `report_format` | `"text" \| "json" \| "csv"` | `"text"` | Output format for the report |
| `parallel_coord` | `bool` | `False` | Enable cross-process fail-fast via `BEHAVE_PRIORITY_COORD_DIR` |

### Hook functions

- `before_scenario_hook(context, scenario)` — skips scenario if fail-fast triggered
- `after_scenario_hook(context, scenario)` — records result, checks fail-fast
- `priority_report(context)` — prints execution report in `after_all`
- `cleanup_parallel_coord(context)` — removes worker file from coordination directory in `after_all`

### `PriorityConfig`

Immutable frozen dataclass with all configuration options. Can be constructed directly for advanced use cases.

### Parser functions

- `parse_priority(tags) -> int | None` — parse `@priority(N)` from a tag list
- `parse_feature_priority(tags) -> int | None` — parse `@feature-priority(N)` from a tag list
- `resolve_priority(scenario_tags, feature_tags, config, rule_tags=None) -> int` — resolve effective priority (scenario > rule > feature > default)
- `is_critical(tags, critical_tag) -> bool` — check if scenario is critical

### Exceptions

- `PriorityError` — base exception for all behave-priority errors
- `PriorityParseError` — raised when a priority tag has invalid syntax

## Architecture

```
behave_priority/
├── __init__.py          # Public exports
├── exceptions.py        # PriorityError, PriorityParseError
├── config.py            # PriorityConfig (frozen dataclass)
├── parser.py            # Tag priority parsing
├── sorter.py            # ScenarioSorter — reorders behave's runner
├── hooks.py             # setup_priority, hook functions, PriorityState
├── parallel.py          # ParallelCoordinator — cross-process fail-fast
└── report.py            # PriorityReport, ReportEntry, ReportSummary
```

### How it works

1. **`before_all`**: `setup_priority()` reads config, sorts features and scenarios by priority
2. **`before_scenario`**: hook skips scenario if fail-fast was triggered
3. **`after_scenario`**: hook records result, checks fail-fast conditions
4. **`after_all`**: `priority_report()` prints execution report if enabled

## Use cases

1. **CI critical-first**: Run `@priority(1)` scenarios first. If any fail, stop immediately. Don't waste 20 minutes on regression.
2. **Smoke tests**: Tag smoke tests `@priority(1) @critical`, run with `stop_on_critical=True`. Get smoke results in 30 seconds.
3. **Time-limited runs**: In PR pipelines with time budget, `order=True` ensures most important tests run first.
4. **Debugging**: `reverse=True` runs obscure/edge-case tests first while you're fresh.

## Requirements

- Python >= 3.11
- behave >= 1.2.6

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check behave_priority/ tests/

# Type check
mypy --strict behave_priority/

# Coverage
pytest --cov=behave_priority --cov-report=term-missing
```

## Limitations

### Parallel execution (`--parallel`)

When behave runs with `--parallel=N`, each worker process gets its own
isolated `PriorityState`. This has the following consequences:

- **Scenario reordering**: Each worker sorts only its own subset of
  scenarios. Global priority ordering across workers is not guaranteed.
  A `@priority(1)` scenario assigned to worker 2 may run after a
  `@priority(5)` scenario in worker 1.
- **Fail-fast (`stop_after_failures`)**: By default, only stops scenarios
  within the same worker. With `parallel_coord=True` and
  `BEHAVE_PRIORITY_COORD_DIR` set, failure counts are aggregated globally
  across all workers. See [Parallel coordination](#parallel-coordination).
- **Critical stop (`stop_on_critical`)**: By default per-worker only.
  With `parallel_coord=True`, a critical failure in any worker triggers
  stop in all workers.
- **Counters**: `failed_count`, `executed_count`, `critical_failed`, and
  `should_stop` are all per-process. The final report reflects only the
  worker that generated it.
- **Reports**: Generated independently per worker. Each worker prints
  its own report covering only the scenarios it executed. There is no
  merged or aggregated report.
- **`time_saved` estimation**: Inaccurate in parallel mode. The
  estimation assumes sequential execution; with N workers, skipped
  scenarios in one worker overlap with execution in others.
- **`priority_tag`**: Scenarios matching the priority tag are sorted
  first within each worker, but not globally across workers.

## License

[MIT](LICENSE)
