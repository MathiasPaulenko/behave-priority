Scenario Sorter
===============

The sorter module reorders behave's feature and scenario lists by priority.

.. autoclass:: behave_priority.sorter.ScenarioLike
   :members:
   :show-inheritance:

.. autoclass:: behave_priority.sorter.FeatureLike
   :members:
   :show-inheritance:

.. autoclass:: behave_priority.sorter.ScenarioSorter
   :members:
   :show-inheritance:

Sorting Algorithm
-----------------

The :class:`~behave_priority.ScenarioSorter` performs a multi-level sort:

1. **Feature-level sorting**: Features are sorted by their "best" (lowest)
   scenario priority. This ensures features with high-priority scenarios
   run first.

2. **Scenario-level sorting**: Within each feature, scenarios are sorted by
   their resolved priority (scenario > rule > feature > default).

3. **Rule-level sorting**: When a feature contains ``Rule`` objects (Gherkin
   v6), each rule's inner scenarios are sorted independently, and the rules
   themselves are sorted among other run items.

Sort Key Computation
--------------------

The sort key is a tuple ``(primary, secondary)``:

- **primary**: ``0`` if the scenario has the ``priority_tag`` (e.g. ``@smoke``),
  ``1`` otherwise. This ensures tagged scenarios run first regardless of
  priority number.
- **secondary**: The resolved priority value. When ``reverse=True``, the
  priority is negated so that higher numbers sort first.

The sort is **stable**: scenarios with the same priority preserve their
original relative order. This is important for Scenario Outlines, which
behave expands into multiple scenarios sharing the same tags (and therefore
the same priority).

Gherkin v6 Rule Handling
------------------------

When a feature's ``run_items`` contains ``Rule`` objects:

1. Each rule's inner ``run_items`` and ``scenarios`` are sorted using the
   rule's tags as an intermediate priority level.
2. Rules are sorted among other run items (scenarios, scenario outlines)
   based on their best inner scenario's sort key.
3. A rule with no inner scenarios gets a sort key of
   ``(1, default_priority)``.

The ``_is_rule`` method detects Rule objects by checking for the presence
of a ``run_items`` attribute. Within ``feature.run_items``, only ``Rule``
objects have this attribute; ``Scenario`` and ``ScenarioOutline`` do not.

Protocols
---------

The module defines two structural protocols:

- :class:`~behave_priority.sorter.ScenarioLike`: Objects with ``name``,
  ``tags``, ``status``, and ``duration`` attributes.
- :class:`~behave_priority.sorter.FeatureLike`: Objects with ``name``,
  ``filename``, ``tags``, and ``scenarios`` attributes.

These protocols allow the sorter to work with behave's model objects without
hard dependencies on behave at runtime.

Examples
--------

Basic sorting:

.. code-block:: python

   from behave_priority import PriorityConfig, ScenarioSorter

   config = PriorityConfig(order=True)
   sorter = ScenarioSorter(config)
   sorter.sort(features)  # Sorts in-place

With smoke tag priority:

.. code-block:: python

   config = PriorityConfig(order=True, priority_tag="smoke")
   sorter = ScenarioSorter(config)
   sorter.sort(features)  # @smoke scenarios run first

Reversed order:

.. code-block:: python

   config = PriorityConfig(order=True, reverse=True)
   sorter = ScenarioSorter(config)
   sorter.sort(features)  # Higher priority numbers first

Feature sorting is controlled by the same config flags. When ``order=True``,
features are sorted by their best scenario's priority. When ``order=False``
and ``reverse=False`` and ``priority_tag`` is ``None``, features preserve
their original order.
