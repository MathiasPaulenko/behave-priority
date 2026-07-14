Tag Priority Parsing
====================

The parser module provides functions for extracting priority values from
behave tag lists and resolving the effective priority for a scenario.

.. autoclass:: behave_priority.parser.Taggable
   :members:
   :show-inheritance:

.. autofunction:: behave_priority.parser.parse_priority
.. autofunction:: behave_priority.parser.parse_feature_priority
.. autofunction:: behave_priority.parser.resolve_priority
.. autofunction:: behave_priority.parser.is_critical

Tag Syntax
----------

Priority tags use a function-like syntax inside Gherkin tags:

.. list-table:: Tag Patterns
   :header-rows: 1
   :widths: 30 20 50

   * - Pattern
     - Scope
     - Description
   * - ``@priority(N)``
     - Scenario, Rule
     - Sets priority to ``N`` (an integer). Lower numbers run first.
   * - ``@feature-priority(N)``
     - Feature
     - Sets the default priority for all scenarios in the feature.

Both positive and negative integers are accepted:

.. code-block:: gherkin

   @priority(1)     # Valid
   @priority(0)     # Valid
   @priority(-5)    # Valid
   @priority(abc)   # Invalid — raises PriorityParseError
   @priority(1.5)   # Invalid — raises PriorityParseError

Tag Normalization
-----------------

Tags are normalized before parsing:

1. Leading/trailing whitespace is stripped.
2. Leading ``@`` characters are removed (behave stores tags without ``@``).

This means ``" @priority(1) "`` and ``"@priority(1)"`` and ``"priority(1)"``
are all equivalent.

Priority Resolution
-------------------

:func:`~behave_priority.resolve_priority` determines the effective priority
for a scenario by checking tags at multiple levels:

.. code-block:: text

   Scenario @priority(N)  →  use N
           ↓ (not found)
   Rule @priority(N)      →  use N
           ↓ (not found)
   Feature @feature-priority(N)  →  use N
           ↓ (not found)
   config.default_priority  →  use default (999)

This cascade ensures that scenarios can override rule-level priorities,
which in turn override feature-level priorities.

Critical Tag Detection
----------------------

:func:`~behave_priority.is_critical` checks whether a tag list contains the
configured critical tag. Both the tags and the ``critical_tag`` parameter are
normalized (stripped of ``@`` and whitespace) before comparison:

.. code-block:: python

   from behave_priority import is_critical

   is_critical(["critical"])            # True
   is_critical(["@critical"])           # True
   is_critical([" critical "])          # True
   is_critical(["smoke"])               # False
   is_critical(["critico"], "critico")  # True (custom critical tag)

Protocol
--------

The :class:`~behave_priority.parser.Taggable` protocol defines the minimum
interface required for tag-based operations. Any object with a ``tags``
attribute (a list of strings) satisfies this protocol.

Examples
--------

Parsing scenario priority:

.. code-block:: python

   from behave_priority import parse_priority

   parse_priority(["smoke", "priority(1)"])      # → 1
   parse_priority(["priority(3)", "priority(1)"])  # → 3 (first match)
   parse_priority(["smoke"])                      # → None
   parse_priority(["priority(abc)"])              # → raises PriorityParseError

Resolving effective priority:

.. code-block:: python

   from behave_priority import PriorityConfig, resolve_priority

   config = PriorityConfig(order=True, default_priority=999)

   # Scenario tag wins
   resolve_priority(["priority(1)"], ["feature-priority(10)"], config)
   # → 1

   # Rule tag wins over feature
   resolve_priority([], ["feature-priority(10)"], config, rule_tags=["priority(3)"])
   # → 3

   # Feature tag wins over default
   resolve_priority([], ["feature-priority(10)"], config)
   # → 10

   # Default fallback
   resolve_priority([], [], config)
   # → 999
