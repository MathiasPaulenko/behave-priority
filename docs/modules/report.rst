Execution Report
================

The report module provides execution report collection, rendering, and
serialization.

ReportEntry
-----------

.. autoclass:: behave_priority.report.ReportEntry
   :members:
   :show-inheritance:

The :class:`~behave_priority.ReportEntry` dataclass represents a single
scenario in the execution report. Each entry is immutable and hashable.

Fields
~~~~~~

.. list-table:: ReportEntry Fields
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``index``
     - ``int``
     - 1-based position in execution order.
   * - ``feature_name``
     - ``str``
     - Name or filename of the parent feature.
   * - ``scenario_name``
     - ``str``
     - Display name of the scenario.
   * - ``priority``
     - ``int``
     - Resolved priority value.
   * - ``status``
     - ``str``
     - Execution status: ``"passed"``, ``"failed"``, ``"skipped"``, etc.
   * - ``duration``
     - ``float``
     - Execution time in seconds.
   * - ``is_critical``
     - ``bool``
     - Whether the scenario has the critical tag (including rule-level).

ReportSummary
-------------

.. autoclass:: behave_priority.report.ReportSummary
   :members:
   :show-inheritance:

The :class:`~behave_priority.ReportSummary` dataclass provides aggregate
statistics across all report entries.

Properties
~~~~~~~~~~

**``time_saved``**: Estimated time saved by fail-fast skipping. Since skipped
scenarios have ``duration=0`` (they never ran), the saved time is estimated
as the average duration of executed (non-skipped) scenarios multiplied by
the number of skipped scenarios.

.. code-block:: python

   time_saved = avg(executed_durations) * skipped_count

**``pass_rate``**: Percentage of passed scenarios excluding skipped ones.
Returns ``0.0`` when no scenarios were executed.

.. code-block:: python

   pass_rate = (passed / (total - skipped)) * 100

PriorityReport
--------------

.. autoclass:: behave_priority.report.PriorityReport
   :members:
   :show-inheritance:
   :special-members: __init__

Methods
~~~~~~~

.. list-table:: PriorityReport Methods
   :header-rows: 1
   :widths: 20 80

   * - Method
     - Description
   * - ``record()``
     - Record a scenario execution result. Called by ``after_scenario_hook``.
   * - ``render()``
     - Render the full report as a formatted string table.
   * - ``summary()``
     - Compute and return a ``ReportSummary`` with aggregate statistics.
   * - ``to_dict()``
     - Serialize the report to a dictionary (JSON-compatible).

Rendered Output
---------------

The ``render()`` method produces a human-readable table:

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

Column widths for Feature and Scenario names are computed dynamically from
the actual content, with a maximum of 40 characters. Names longer than the
computed width are truncated with ``...``. The minimum column width is the
length of the header label (``"Feature"`` or ``"Scenario"``) to ensure
proper alignment.

Dictionary Serialization
------------------------

The ``to_dict()`` method returns a JSON-compatible dictionary:

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
           },
           ...
       ],
       "summary": {
           "total": 3,
           "passed": 1,
           "failed": 1,
           "skipped": 1,
           "undefined": 0,
           "critical_total": 1,
           "critical_passed": 0,
           "critical_failed": 0,
           "total_duration": 1.68,
           "skipped_duration": 0.0,
           "pass_rate": 50.0,
           "time_saved": 1.23
       }
   }

This format is suitable for REST API responses, file storage, or further
processing.

Examples
--------

Recording scenarios:

.. code-block:: python

   from behave_priority import PriorityConfig, PriorityReport

   config = PriorityConfig()
   report = PriorityReport(config)

   report.record(
       scenario_name="Login test",
       feature_name="Auth",
       priority=1,
       status="passed",
       duration=1.5,
       is_critical=True,
   )

Getting summary statistics:

.. code-block:: python

   summary = report.summary()
   print(f"Pass rate: {summary.pass_rate:.1f}%")
   print(f"Time saved: {summary.time_saved:.2f}s")

Exporting to JSON:

.. code-block:: python

   import json

   data = report.to_dict()
   json_str = json.dumps(data, indent=2)
