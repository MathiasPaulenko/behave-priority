Reports Guide
=============

This guide covers the execution report system in detail.

Enabling Reports
----------------

To enable the printed report, pass ``report=True`` to ``setup_priority``:

.. code-block:: python

   setup_priority(context, order=True, report=True)

Then call ``priority_report(context)`` in ``after_all``:

.. code-block:: python

   def after_all(context):
       priority_report(context)

Report Output
-------------

The rendered report includes:

1. **Header**: Title and separator.
2. **Table**: One row per scenario with index, priority, feature, scenario
   name, status, and duration.
3. **Summary**: Aggregate statistics including critical scenario results,
   totals, and estimated time saved.

Example:

.. code-block:: text

   Priority Execution Report
   =========================

     #  Priority  Feature   Scenario          Status    Duration
   ------------------------------------------------------------------
     1         1  Login     Successful login  passed       1.23s
     2         2  Login     Failed login      failed       0.45s
     3         3  Login     Account locked    skipped      0.00s

   Summary:
     Critical: 0/1 passed
     Total: 1 passed, 1 failed, 1 skipped
     Time saved by fail-fast: 1.23s (estimated, 1 scenario(s) skipped)

Column Widths
-------------

Column widths for Feature and Scenario names are computed dynamically:

- The width is the maximum of all entry names and the header label length.
- Width is capped at 40 characters.
- Names longer than the column width are truncated with ``...``.

This ensures proper alignment regardless of name lengths.

Programmatic Access
-------------------

Use ``get_report(context)`` to access the ``PriorityReport`` object:

.. code-block:: python

   from behave_priority import get_report

   def after_all(context):
       report = get_report(context)
       if report is None:
           return

       summary = report.summary()
       print(f"Pass rate: {summary.pass_rate:.1f}%")
       print(f"Total: {summary.total}")
       print(f"Failed: {summary.failed}")
       print(f"Time saved: {summary.time_saved:.2f}s")

JSON Export
-----------

Use ``to_dict()`` to get a JSON-compatible dictionary:

.. code-block:: python

   import json
   from behave_priority import get_report

   def after_all(context):
       report = get_report(context)
       if report:
           data = report.to_dict()
           with open("priority-report.json", "w") as f:
               json.dump(data, f, indent=2)

The dictionary structure:

.. code-block:: python

   {
       "entries": [
           {
               "index": 1,
               "feature_name": "Login",
               "scenario_name": "Successful login",
               "priority": 1,
               "status": "passed",
               "duration": 1.23,
               "is_critical": False
           }
       ],
       "summary": {
           "total": 1,
           "passed": 1,
           "failed": 0,
           "skipped": 0,
           "undefined": 0,
           "critical_total": 0,
           "critical_passed": 0,
           "critical_failed": 0,
           "total_duration": 1.23,
           "skipped_duration": 0.0,
           "pass_rate": 100.0,
           "time_saved": 0.0
       }
   }

Time Saved Estimation
---------------------

Skipped scenarios have ``duration=0`` because they never executed. To
provide a meaningful "time saved" metric, the report estimates the saved
time as:

.. code-block:: text

   time_saved = average(executed_durations) * skipped_count

Where:

- ``executed_durations`` = durations of all non-skipped scenarios
- ``skipped_count`` = number of skipped scenarios

If no scenarios were executed (all skipped), ``time_saved`` is ``0.0``.

Pass Rate
---------

The pass rate excludes skipped scenarios from the denominator:

.. code-block:: text

   pass_rate = (passed / (total - skipped)) * 100

This gives a more meaningful pass rate for fail-fast runs where many
scenarios may be skipped.

Custom Report Processing
------------------------

You can iterate over report entries for custom processing:

.. code-block:: python

   from behave_priority import get_report

   def after_all(context):
       report = get_report(context)
       if report is None:
           return

       for entry in report._entries:
           if entry.status == "failed":
               print(f"FAILED: {entry.scenario_name} (priority: {entry.priority})")

       summary = report.summary()
       if summary.critical_failed:
           print("WARNING: Critical scenarios failed!")
