Configuration
=============

The :class:`~behave_priority.PriorityConfig` dataclass controls all behavior
of ``behave-priority``. It is immutable (frozen) and validated at construction
time.

.. autoclass:: behave_priority.config.PriorityConfig
   :members:
   :show-inheritance:

Configuration Fields
--------------------

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 15 10 50

   * - Field
     - Type
     - Default
     - Description
   * - ``order``
     - ``bool``
     - ``False``
     - Sort scenarios by priority (highest first). When ``True``, scenarios
       are reordered so that lower priority numbers execute first.
   * - ``reverse``
     - ``bool``
     - ``False``
     - Reverse sort order. When ``True``, higher priority numbers execute
       first. Useful when priority numbers represent severity rather than
       execution order.
   * - ``priority_tag``
     - ``str | None``
     - ``None``
     - Tag name to run first (e.g. ``"smoke"``). Scenarios with this tag
       are moved to the front of execution, before any priority-based
       sorting.
   * - ``stop_after_failures``
     - ``int | None``
     - ``None``
     - Stop after N failed scenarios. ``None`` disables this fail-fast
       strategy. Must be a positive integer if provided.
   * - ``stop_on_critical``
     - ``bool``
     - ``False``
     - Stop execution if any scenario tagged ``@critical`` fails.
   * - ``critical_tag``
     - ``str``
     - ``"critical"``
     - Tag name that marks a scenario as critical. Both the tag and the
       ``critical_tag`` config value are normalized (stripped of ``@``
       prefix and whitespace) before comparison.
   * - ``default_priority``
     - ``int``
     - ``999``
     - Priority assigned to scenarios without any priority tag. Must be
       non-negative.
   * - ``report``
     - ``bool``
     - ``False``
     - Print the execution report after the run via
       :func:`~behave_priority.priority_report`.

Validation
----------

The following validations are performed at construction time:

- ``stop_after_failures`` must be a positive integer or ``None``.
- ``critical_tag`` must not be an empty string.
- ``priority_tag`` must not be an empty string if provided (``None`` is valid).
- ``default_priority`` must be non-negative.

Invalid values raise ``ValueError`` with a descriptive message.

Examples
--------

Basic priority ordering:

.. code-block:: python

   from behave_priority import PriorityConfig

   config = PriorityConfig(order=True)

Priority ordering with fail-fast:

.. code-block:: python

   config = PriorityConfig(
       order=True,
       stop_after_failures=3,
       report=True,
   )

Smoke tests first, stop on critical failure:

.. code-block:: python

   config = PriorityConfig(
       order=True,
       priority_tag="smoke",
       stop_on_critical=True,
       critical_tag="critical",
       report=True,
   )

Reversed order (highest priority number first):

.. code-block:: python

   config = PriorityConfig(order=True, reverse=True)

Custom default priority:

.. code-block:: python

   config = PriorityConfig(order=True, default_priority=100)

Immutability
------------

``PriorityConfig`` is a frozen dataclass with ``slots=True``. Once created,
its fields cannot be modified:

.. code-block:: python

   config = PriorityConfig(order=True)
   config.order = False  # Raises FrozenInstanceError

This ensures that configuration remains consistent throughout the test run.
