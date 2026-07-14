Feature: Fail-fast behavior

  @priority(1)
  Scenario: First scenario passes
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  @priority(2)
  Scenario: Second scenario fails
    Given a step that fails
    When the scenario runs
    Then the scenario should complete

  @priority(3)
  Scenario: Third scenario should be skipped
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

  @priority(4)
  Scenario: Fourth scenario should be skipped
    Given a step that passes
    When the scenario runs
    Then the scenario should complete
