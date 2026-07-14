@feature-priority(5)
Feature: Priority ordering

  @priority(1)
  Scenario: High priority scenario
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  @priority(3)
  Scenario: Medium priority scenario
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  @priority(2)
  Scenario: Low priority scenario
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  Scenario: No priority tag scenario
    Given a step that passes
    When the scenario runs
    Then the scenario should complete
