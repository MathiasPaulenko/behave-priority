Feature: Smoke tag priority

  @smoke
  Scenario: Smoke tagged scenario
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  Scenario: Regular scenario without smoke tag
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  @priority(1)
  Scenario: High priority but no smoke
    Given a step that passes
    When the scenario runs
    Then the scenario should complete
