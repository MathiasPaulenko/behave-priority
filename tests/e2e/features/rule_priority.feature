Feature: Rule support with priority

  @priority(3)
  Scenario: Standalone scenario before rule
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  Rule: High priority rule

    @priority(1)
    Scenario: Rule scenario with high priority
      Given a step that passes
      When the scenario runs
      Then the scenario should complete

  Rule: Low priority rule

    @priority(5)
    Scenario: Rule scenario with low priority
      Given a step that passes
      When the scenario runs
      Then the scenario should complete
