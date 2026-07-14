Feature: Scenario outline with priority

  @priority(1)
  Scenario Outline: Outline scenario with examples
    Given a step that passes
    When the scenario runs
    Then the scenario should complete

    Examples:
      | value |
      | a     |
      | b     |
      | c     |

  @priority(3)
  Scenario: Scenario after outline
    Given a step that passes
    When the scenario runs
    Then the scenario should complete
