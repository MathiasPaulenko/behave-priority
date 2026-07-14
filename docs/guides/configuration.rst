Configuration Guide
===================

This guide covers all configuration options in detail.

Basic Configuration
-------------------

The simplest configuration enables priority ordering:

.. code-block:: python

   setup_priority(context, order=True)

This sorts scenarios by ``@priority(N)`` tags (lowest first) and features
by their best scenario's priority.

Full Configuration
------------------

All available options:

.. code-block:: python

   setup_priority(
       context,
       order=True,              # Sort by priority
       reverse=False,           # Reverse sort (highest first)
       priority_tag="smoke",    # Run @smoke scenarios first
       stop_after_failures=3,   # Stop after 3 failures
       stop_on_critical=True,   # Stop if @critical fails
       critical_tag="critical", # Custom critical tag name
       default_priority=999,    # Priority for untagged scenarios
       report=True,             # Print report after run
   )

Option Details
--------------

order
~~~~~

When ``True``, scenarios within each feature are sorted by their resolved
priority. Features are also sorted by their best (lowest) scenario priority.

When ``False``, no sorting occurs. Scenarios run in behave's default order
(file order).

reverse
~~~~~~~

When ``True``, the sort order is reversed: higher priority numbers run first.
This is useful when priority represents severity (e.g. priority 5 = most
severe = should run first).

Only effective when ``order=True``.

priority_tag
~~~~~~~~~~~~

A tag name (without ``@``) that marks scenarios to run first, regardless of
their priority number. Scenarios with this tag get a primary sort key of
``0``, while all others get ``1``.

Common use case: ``priority_tag="smoke"`` runs all ``@smoke`` scenarios
before any other scenarios, even if they have higher priority numbers.

stop_after_failures
~~~~~~~~~~~~~~~~~~~

Stop execution after N scenarios fail. Remaining scenarios are skipped and
recorded in the report.

Set to ``None`` to disable this fail-fast strategy.

Must be a positive integer if provided. ``0`` and negative values raise
``ValueError``.

stop_on_critical
~~~~~~~~~~~~~~~~

When ``True``, execution stops immediately after any scenario tagged
``@critical`` (or the configured ``critical_tag``) fails.

This is useful for smoke tests where a critical failure means the rest of
the suite is meaningless.

critical_tag
~~~~~~~~~~~~

The tag name that marks a scenario as critical. Defaults to ``"critical"``.

Both the tag and this config value are normalized (stripped of ``@`` prefix
and whitespace) before comparison, so ``"@critical"`` and ``"critical"`` are
equivalent.

default_priority
~~~~~~~~~~~~~~~~

The priority assigned to scenarios without any ``@priority(N)`` tag. Defaults
to ``999``, which places untagged scenarios last.

Must be non-negative.

report
~~~~~~

When ``True``, the execution report is printed to stdout via
``priority_report(context)`` in ``after_all``.

The report can also be accessed programmatically via ``get_report(context)``
regardless of this setting.

Validation Errors
-----------------

Invalid configuration raises ``ValueError`` at construction time:

.. code-block:: python

   PriorityConfig(stop_after_failures=0)    # ValueError
   PriorityConfig(stop_after_failures=-1)   # ValueError
   PriorityConfig(critical_tag="")          # ValueError
   PriorityConfig(priority_tag="")          # ValueError
   PriorityConfig(default_priority=-1)      # ValueError

Immutability
------------

``PriorityConfig`` is frozen and uses ``slots=True`` for memory efficiency.
Once created, it cannot be modified. This ensures consistent behavior
throughout the test run.

Common Patterns
---------------

Smoke tests first with fail-fast:

.. code-block:: python

   setup_priority(
       context,
       order=True,
       priority_tag="smoke",
       stop_on_critical=True,
       report=True,
   )

CI pipeline with failure threshold:

.. code-block:: python

   setup_priority(
       context,
       order=True,
       stop_after_failures=5,
       report=True,
   )

Severity-based ordering (highest number = most severe = runs first):

.. code-block:: python

   setup_priority(
       context,
       order=True,
       reverse=True,
       report=True,
   )

No sorting, just fail-fast and reporting:

.. code-block:: python

   setup_priority(
       context,
       stop_after_failures=1,
       report=True,
   )
