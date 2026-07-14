Behave Hooks
============

The hooks module provides the integration layer between ``behave-priority``
and behave's lifecycle. It exposes functions for ``before_all``,
``before_scenario``, ``after_scenario``, and ``after_all`` hooks.

.. autodata:: behave_priority.hooks._scenario_key
   :no-index:

.. autofunction:: behave_priority.hooks.setup_priority
.. autofunction:: behave_priority.hooks.before_scenario_hook
.. autofunction:: behave_priority.hooks.after_scenario_hook
.. autofunction:: behave_priority.hooks.get_report
.. autofunction:: behave_priority.hooks.priority_report

PriorityState
-------------

.. autoclass:: behave_priority.hooks.PriorityState
   :members:
   :show-inheritance:

The :class:`~behave_priority.PriorityState` dataclass holds all mutable
execution state that persists across hooks via ``context._priority_state``.

.. note::

   This state is **not shared across processes**. When behave runs with
   ``--parallel``, each worker process gets its own isolated
   ``PriorityState``. Fail-fast, counters, and reports are per-process
   and not coordinated across workers.

State Fields
~~~~~~~~~~~~

.. list-table:: PriorityState Fields
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``config``
     - ``PriorityConfig``
     - The priority configuration for this run.
   * - ``report``
     - ``PriorityReport``
     - The execution report collector.
   * - ``sorter``
     - ``ScenarioSorter``
     - The sorter instance used to reorder scenarios.
   * - ``failed_count``
     - ``int``
     - Number of failed scenarios so far.
   * - ``critical_failed``
     - ``bool``
     - Whether any critical scenario has failed.
   * - ``should_stop``
     - ``bool``
     - Whether fail-fast conditions have been triggered.
   * - ``executed_count``
     - ``int``
     - Number of scenarios actually executed (excludes skipped).
   * - ``skipped_count``
     - ``int``
     - Number of scenarios skipped by fail-fast.
   * - ``priority_map``
     - ``dict[str, int]``
     - Maps scenario key to resolved priority.
   * - ``feature_map``
     - ``dict[str, str]``
     - Maps scenario key to parent feature name.
   * - ``rule_tag_map``
     - ``dict[str, list[str]]``
     - Maps scenario key to parent rule tags (Gherkin v6).

Fail-Fast Logic
---------------

The ``check_fail_fast`` method evaluates two conditions:

1. **stop_after_failures**: If ``failed_count >= stop_after_failures``,
   returns ``True``.
2. **stop_on_critical**: If ``stop_on_critical`` is enabled and
   ``critical_failed`` is ``True``, returns ``True``.

If either condition is met, ``should_stop`` is set to ``True`` and all
subsequent scenarios are skipped via ``before_scenario_hook``.

Scenario Key Generation
-----------------------

The internal ``_scenario_key`` function builds a deterministic key for each
scenario:

- If the scenario has ``filename`` and ``line`` attributes (as behave
  provides), the key is ``"{filename}:{line}"``.
- Otherwise, falls back to ``"id:{id(scenario)}"``.

This key is used to look up priority, feature name, and rule tags in the
state maps.

Hook Lifecycle
--------------

.. code-block:: text

   before_all(context)
     └─ setup_priority(context, ...)
          ├─ Create PriorityConfig
          ├─ Access runner.features
          ├─ Sort features & scenarios
          ├─ Populate priority_map, feature_map, rule_tag_map
          └─ Store PriorityState in context._priority_state

   before_scenario(context, scenario)
     └─ before_scenario_hook(context, scenario)
          └─ If should_stop: scenario.skip("fail-fast triggered")

   after_scenario(context, scenario)
     └─ after_scenario_hook(context, scenario)
          ├─ Record scenario in report
          ├─ If skipped: update should_stop, return
          ├─ Increment executed_count
          ├─ If failed: increment failed_count, check critical
          └─ Update should_stop

   after_all(context)
     └─ priority_report(context)
          └─ If config.report: print report

Integration Example
-------------------

.. code-block:: python

   from behave_priority import (
       setup_priority,
       before_scenario_hook,
       after_scenario_hook,
       priority_report,
       get_report,
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
       # Optionally access the report programmatically:
       report = get_report(context)
       if report:
           data = report.to_dict()
           print(f"Pass rate: {data['summary']['pass_rate']:.1f}%")

Programmatic Report Access
--------------------------

Use :func:`~behave_priority.get_report` to access the
:class:`~behave_priority.PriorityReport` object after a run, without
accessing ``context._priority_state`` directly:

.. code-block:: python

   from behave_priority import get_report

   def after_all(context):
       report = get_report(context)
       if report:
           summary = report.summary()
           print(f"Executed: {summary.passed} passed, {summary.failed} failed")
           print(f"Time saved: {summary.time_saved:.2f}s")
