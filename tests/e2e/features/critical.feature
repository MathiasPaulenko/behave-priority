@critical
Feature: Critical scenario handling

  @priority(1)
  Scenario: Critical scenario passes
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  @priority(2)
  @critical
  Scenario: Critical scenario fails
    Given a step that fails
    When the scenario runs
    Then the scenario should complete

  @priority(3)
  Scenario: Non-critical scenario after critical failure
    Given a step that passes
    When the scenario runs
    Then the scenario should complete
