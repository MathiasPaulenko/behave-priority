behave-priority
===============

Priority-based execution, fail-fast, and reporting for **Behave BDD**.

.. image:: https://img.shields.io/badge/python-3.11%2B-blue.svg
   :alt: Python 3.11+

.. image:: https://img.shields.io/badge/behave-1.2.6%2B-green.svg
   :alt: Behave 1.2.6+

Overview
--------

``behave-priority`` extends `Behave <https://github.com/behave/behave>`_ with:

- **Priority-based scenario ordering** — sort scenarios by ``@priority(N)`` tags.
- **Gherkin v6 Rule support** — sort scenarios inside ``Rule`` blocks, with
  rule-level tags as an intermediate priority level.
- **Fail-fast execution** — stop after N failures or on critical scenario failure.
- **Execution reports** — detailed tables with priorities, statuses, durations,
  and estimated time saved by fail-fast.
- **Critical scenario tracking** — mark scenarios as ``@critical`` and track
  their pass/fail status separately.
- **Priority tags** — run specific tagged scenarios (e.g. ``@smoke``) first.
- **Programmatic configuration** — no CLI flags, all config via Python.
- **97% test coverage** — comprehensive unit, integration, and E2E tests.

Installation
------------

.. code-block:: bash

   pip install behave-priority

Or from source:

.. code-block:: bash

   git clone https://github.com/MathiasPaulenko/behave-priority.git
   cd behave-priority
   pip install -e .

Quick Start
-----------

1. Add priority tags to your ``.feature`` files:

.. code-block:: gherkin

   @feature-priority(10)
   Feature: Login

     @priority(1)
     Scenario: Successful login
       Given I am on the login page
       When I enter valid credentials
       Then I should be logged in

     @priority(2)
     Scenario: Failed login
       Given I am on the login page
       When I enter invalid credentials
       Then I should see an error

     @critical
     Scenario: Account locked after 3 attempts
       Given I am on the login page
       When I enter wrong credentials 3 times
       Then my account should be locked

2. Configure ``behave-priority`` in your ``environment.py``:

.. code-block:: python

   from behave_priority import setup_priority, before_scenario_hook, after_scenario_hook, priority_report


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

3. Run behave normally:

.. code-block:: bash

   behave

Priority Resolution
-------------------

Priority determines the execution order of scenarios. Lower numbers run first.

Precedence (highest to lowest):

1. **Scenario tags** — ``@priority(N)`` on the scenario itself.
2. **Rule tags** — ``@priority(N)`` on the parent ``Rule`` (Gherkin v6).
3. **Feature tags** — ``@feature-priority(N)`` on the parent feature.
4. **Default priority** — ``config.default_priority`` (default: ``999``).

Example with all levels:

.. code-block:: gherkin

   @feature-priority(10)
   Feature: Shopping Cart

     @priority(3)
     Rule: Checkout flow
       @priority(1)
       Scenario: Pay with credit card
         # Priority: 1 (scenario overrides rule)

       Scenario: Pay with PayPal
         # Priority: 3 (inherits from rule)

     Scenario: View cart
       # Priority: 10 (inherits from feature)

Tag Reference
-------------

.. list-table:: Tag Syntax
   :header-rows: 1
   :widths: 30 20 50

   * - Tag
     - Scope
     - Description
   * - ``@priority(N)``
     - Scenario, Rule
     - Sets the priority for this scenario or all scenarios within a rule.
   * - ``@feature-priority(N)``
     - Feature
     - Sets the default priority for all scenarios in the feature.
   * - ``@critical``
     - Scenario, Rule
     - Marks the scenario as critical. Fail-fast can trigger on critical failures.
   * - ``@smoke`` (or any tag)
     - Scenario
     - Can be configured as ``priority_tag`` to run those scenarios first.

Fail-Fast Behavior
------------------

``behave-priority`` supports two fail-fast strategies:

**Stop after N failures** (``stop_after_failures=N``):

   Execution stops after N scenarios fail. Remaining scenarios are skipped
   and recorded in the report with ``"skipped"`` status.

**Stop on critical failure** (``stop_on_critical=True``):

   Execution stops immediately after any scenario tagged ``@critical`` fails.
   This is useful for smoke tests where a critical failure means the rest
   of the suite is meaningless.

Both strategies can be combined. When fail-fast triggers, ``before_scenario``
calls ``scenario.skip("fail-fast triggered")`` and ``after_scenario`` records
the skipped scenario in the report.

.. note::

   When behave runs with ``--parallel``, each worker process gets its own
   isolated ``PriorityState``. By default, fail-fast, counters, and reports
   are per-process and not coordinated across workers.

   To coordinate fail-fast across workers, set the
   ``BEHAVE_PRIORITY_COORD_DIR`` environment variable to a shared directory
   and pass ``parallel_coord=True`` to :func:`~behave_priority.setup_priority`.
   Each worker writes its failure state to a JSON file in the coordination
   directory. ``stop_after_failures`` and ``stop_on_critical`` are then
   evaluated globally across all workers. Call
   :func:`~behave_priority.cleanup_parallel_coord` in ``after_all`` to remove
   the worker's file.

   .. code-block:: bash

      export BEHAVE_PRIORITY_COORD_DIR=/tmp/behave_priority_coord
      behave --parallel=4

   .. code-block:: python

      setup_priority(
          context,
          order=True,
          stop_after_failures=3,
          parallel_coord=True,
      )

Execution Report
----------------

When ``report=True`` is passed to ``setup_priority``, a formatted report is
printed after the run via ``priority_report(context)``.

Example output:

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

The report can also be accessed programmatically via ``get_report(context)``
which returns a :class:`~behave_priority.PriorityReport` object.

**Report formats** — use ``report_format`` to control output:

- ``report_format="text"`` (default) — human-readable table with summary.
- ``report_format="json"`` — machine-readable JSON with entries and summary.
  Useful for CI/CD integration.
- ``report_format="csv"`` — CSV with one row per scenario entry.

.. code-block:: python

   setup_priority(
       context,
       order=True,
       report=True,
       report_format="json",
   )

Gherkin v6 Rule Support
-----------------------

``behave-priority`` fully supports Gherkin v6 ``Rule`` blocks:

- Scenarios inside a ``Rule`` are sorted by priority, using rule-level tags
  as an intermediate priority level.
- ``@critical`` on a ``Rule`` marks all scenarios within as critical.
- ``@priority(N)`` on a ``Rule`` provides a default priority for scenarios
  that don't have their own ``@priority`` tag.
- Rules themselves are sorted among other run items in a feature.

API Reference
-------------

.. toctree::
   :maxdepth: 2
   :caption: Modules

   modules/config
   modules/parser
   modules/sorter
   modules/hooks
   modules/parallel
   modules/report
   modules/exceptions

.. toctree::
   :maxdepth: 1
   :caption: Guides

   guides/configuration
   guides/gherkin_v6
   guides/integration
   guides/reports

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
