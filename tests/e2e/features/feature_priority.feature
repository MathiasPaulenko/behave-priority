@feature-priority(10)
Feature: Feature-level priority

  Scenario: Scenario without priority tag inherits feature priority
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  @priority(2)
  Scenario: Scenario with explicit priority overrides feature
    Given a step that passes
    When the scenario runs
    Then the scenario should complete
