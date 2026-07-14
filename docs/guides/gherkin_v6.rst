Gherkin v6 Rule Support
=======================

``behave-priority`` provides full support for Gherkin v6 ``Rule`` blocks,
including priority sorting, critical tag detection, and fail-fast behavior.

What is a Rule?
---------------

Gherkin v6 introduced the ``Rule`` keyword as a container within a
``Feature``. A Rule groups related scenarios and can have its own tags
and background:

.. code-block:: gherkin

   Feature: Shopping Cart

     @priority(5)
     Rule: Checkout flow
       Scenario: Pay with credit card
         Given I have items in my cart
         When I select credit card payment
         Then I should be charged

       Scenario: Pay with PayPal
         Given I have items in my cart
         When I select PayPal payment
         Then I should be redirected to PayPal

     Scenario: View cart
       Given I have items in my cart
       When I view my cart
       Then I should see my items

Priority Resolution with Rules
------------------------------

When a scenario is inside a Rule, the priority resolution cascade is:

1. **Scenario tags** — ``@priority(N)`` on the scenario itself.
2. **Rule tags** — ``@priority(N)`` on the parent Rule.
3. **Feature tags** — ``@feature-priority(N)`` on the parent Feature.
4. **Default** — ``config.default_priority``.

Example:

.. code-block:: gherkin

   @feature-priority(10)
   Feature: Shopping Cart

     @priority(3)
     Rule: Checkout flow

       @priority(1)
       Scenario: Pay with credit card
         # Priority: 1 (scenario tag wins)

       Scenario: Pay with PayPal
         # Priority: 3 (inherits from rule)

     Scenario: View cart
       # Priority: 10 (inherits from feature)

Sorting with Rules
------------------

The sorter handles Rules at two levels:

1. **Within a Rule**: Inner scenarios are sorted by their resolved priority,
   using the rule's tags as an intermediate level.

2. **Among run items**: Rules are sorted alongside standalone scenarios in
   ``feature.run_items``. A Rule's sort key is the minimum (best) sort key
   of its inner scenarios.

This means a Rule containing a ``@priority(1)`` scenario will be ordered
before a standalone ``@priority(2)`` scenario.

Critical Tags on Rules
----------------------

When a Rule is tagged ``@critical``, all scenarios within that Rule are
treated as critical. The ``rule_tag_map`` in ``PriorityState`` tracks
rule tags per scenario, and ``after_scenario_hook`` combines
``scenario.tags + rule_tags`` when evaluating ``is_critical``.

Example:

.. code-block:: gherkin

   Feature: Authentication

     @critical
     Rule: Login security
       Scenario: Brute force protection
         # is_critical = True (inherits from rule)

       Scenario: Session timeout
         # is_critical = True (inherits from rule)

     Scenario: Remember me checkbox
       # is_critical = False (no critical tag)

Rule Detection
--------------

The sorter detects Rule objects by checking for the presence of a
``run_items`` attribute. Within ``feature.run_items``, only ``Rule``
objects have this attribute; ``Scenario`` and ``ScenarioOutline`` do not.

This approach is more robust than checking class names or type
hierarchies, as it works with behave's internal model without hard
dependencies.

Edge Cases
----------

**Empty Rule**: A Rule with no scenarios gets a sort key of
``(1, default_priority)`` and does not affect the sort order of other
items.

**Rule with no run_items**: If ``rule.run_items`` is ``None``, the sorter
still sorts ``rule.scenarios`` if present.

**Mixed run_items**: A feature can have a mix of standalone scenarios and
Rules in its ``run_items``. Both are sorted together using their respective
sort keys.

**Nested tags**: Tags on a Rule do not propagate to the feature level.
They only affect scenarios within that Rule.
