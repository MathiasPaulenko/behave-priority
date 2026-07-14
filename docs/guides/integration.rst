Integration Guide
=================

This guide shows how to integrate ``behave-priority`` into your behave
project.

Minimal Integration
-------------------

Add this to your ``environment.py``:

.. code-block:: python

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

Full Integration
----------------

With all features enabled:

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
           priority_tag="smoke",
           stop_after_failures=3,
           stop_on_critical=True,
           critical_tag="critical",
           default_priority=999,
           report=True,
       )


   def before_scenario(context, scenario):
       before_scenario_hook(context, scenario)


   def after_scenario(context, scenario):
       after_scenario_hook(context, scenario)


   def after_all(context):
       priority_report(context)

       # Programmatic access to report data
       report = get_report(context)
       if report:
           summary = report.summary()
           print(f"\nPass rate: {summary.pass_rate:.1f}%")
           print(f"Time saved: {summary.time_saved:.2f}s")

Conditional Configuration
-------------------------

You can configure ``behave-priority`` differently based on environment
variables or other runtime conditions:

.. code-block:: python

   import os
   from behave_priority import setup_priority


   def before_all(context):
       is_ci = os.environ.get("CI") == "true"

       setup_priority(
           context,
           order=True,
           stop_after_failures=5 if is_ci else None,
           stop_on_critical=is_ci,
           report=True,
       )

Using with behave's --tags
--------------------------

``behave-priority`` works alongside behave's native ``--tags`` filtering.
Behave filters scenarios before ``before_all`` runs, so the sorter only
sees the filtered set. This means:

- ``behave --tags=@smoke`` will only sort smoke-tagged scenarios.
- ``behave --tags=~@wip`` will exclude WIP scenarios from sorting.

The ``priority_tag`` config is different from ``--tags``: it doesn't filter
scenarios, it just moves tagged scenarios to the front of execution order.

Parallel Execution
-------------------

When behave runs with ``--parallel``, each worker process gets its own
isolated ``PriorityState``. This means:

- Sorting is applied per-worker (each worker sorts its assigned features).
- Fail-fast is per-worker (one worker's failure doesn't stop others).
- Counters and reports are per-worker.
- The final report may not include all scenarios.

For accurate reporting in parallel mode, collect reports from each worker
and merge them manually.

Debugging
---------

If scenarios are not being reordered, check:

1. **``setup_priority`` is called in ``before_all``**: The function needs
   access to ``context._runner`` which is only available in ``before_all``.

2. **Runner is accessible**: If behave's internal structure changes, the
   function emits a ``RuntimeWarning`` and returns without sorting.

3. **``order=True`` is set**: Without ``order=True``, no sorting occurs.

4. **Tags are correctly formatted**: ``@priority(1)`` not ``@priority=1``
   or ``@priority:1``.

5. **Feature file syntax is valid**: Run ``behave --dry-run`` to verify
   Gherkin parsing.
