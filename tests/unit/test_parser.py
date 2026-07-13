"""Unit tests for behave_priority.parser."""

from __future__ import annotations

import pytest

from behave_priority.config import PriorityConfig
from behave_priority.exceptions import PriorityParseError
from behave_priority.parser import (
    is_critical,
    parse_feature_priority,
    parse_priority,
    resolve_priority,
)


class TestParsePriority:
    def test_normal_priority(self) -> None:
        assert parse_priority(["priority(1)", "critical"]) == 1

    def test_priority_zero(self) -> None:
        assert parse_priority(["priority(0)"]) == 0

    def test_priority_negative(self) -> None:
        assert parse_priority(["priority(-5)"]) == -5

    def test_priority_large_number(self) -> None:
        assert parse_priority(["priority(99999)"]) == 99999

    def test_no_priority_tag(self) -> None:
        assert parse_priority(["critical", "smoke"]) is None

    def test_multiple_priority_tags_first_wins(self) -> None:
        assert parse_priority(["priority(1)", "priority(3)"]) == 1

    def test_malformed_non_integer(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid priority tag"):
            parse_priority(["priority(abc)"])

    def test_no_parens_ignored(self) -> None:
        assert parse_priority(["priority"]) is None

    def test_empty_parens_raises(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid priority tag"):
            parse_priority(["priority()"])

    def test_whitespace_in_parens(self) -> None:
        assert parse_priority(["priority( 1 )"]) == 1

    def test_whitespace_around_tag(self) -> None:
        assert parse_priority(["  priority(1)  "]) == 1

    def test_empty_tag_list(self) -> None:
        assert parse_priority([]) is None

    def test_priority_not_first_tag(self) -> None:
        assert parse_priority(["smoke", "regression", "priority(5)"]) == 5

    def test_priority_with_other_paren_tags(self) -> None:
        assert parse_priority(["tag(1)", "priority(2)"]) == 2

    def test_priority_float_raises(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid priority tag"):
            parse_priority(["priority(1.5)"])

    def test_priority_plus_sign_raises(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid priority tag"):
            parse_priority(["priority(+1)"])

    def test_priority_double_negative_raises(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid priority tag"):
            parse_priority(["priority(--1)"])

    def test_priority_trailing_text_raises(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid priority tag"):
            parse_priority(["priority(1abc)"])

    def test_at_prefix_priority(self) -> None:
        assert parse_priority(["@priority(1)"]) == 1

    def test_at_prefix_with_whitespace(self) -> None:
        assert parse_priority(["  @priority(5)  "]) == 5

    def test_at_prefix_malformed_raises(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid priority tag"):
            parse_priority(["@priority(abc)"])

    def test_at_prefix_no_closing_paren_raises(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid priority tag"):
            parse_priority(["@priority(1"])


class TestParseFeaturePriority:
    def test_normal_feature_priority(self) -> None:
        assert parse_feature_priority(["feature-priority(2)"]) == 2

    def test_feature_priority_zero(self) -> None:
        assert parse_feature_priority(["feature-priority(0)"]) == 0

    def test_feature_priority_negative(self) -> None:
        assert parse_feature_priority(["feature-priority(-3)"]) == -3

    def test_no_feature_priority_tag(self) -> None:
        assert parse_feature_priority(["critical", "smoke"]) is None

    def test_multiple_feature_priority_tags_first_wins(self) -> None:
        assert parse_feature_priority(["feature-priority(1)", "feature-priority(5)"]) == 1

    def test_malformed_feature_priority(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid feature-priority tag"):
            parse_feature_priority(["feature-priority(abc)"])

    def test_empty_parens_raises(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid feature-priority tag"):
            parse_feature_priority(["feature-priority()"])

    def test_whitespace_in_parens(self) -> None:
        assert parse_feature_priority(["feature-priority( 3 )"]) == 3

    def test_empty_tag_list(self) -> None:
        assert parse_feature_priority([]) is None

    def test_does_not_match_scenario_priority(self) -> None:
        assert parse_feature_priority(["priority(1)"]) is None

    def test_does_not_match_partial_prefix(self) -> None:
        assert parse_feature_priority(["feature-priority(1)"]) is not None
        assert parse_feature_priority(["feature-prio(1)"]) is None

    def test_feature_priority_float_raises(self) -> None:
        with pytest.raises(PriorityParseError, match="Invalid feature-priority tag"):
            parse_feature_priority(["feature-priority(2.5)"])

    def test_at_prefix_feature_priority(self) -> None:
        assert parse_feature_priority(["@feature-priority(3)"]) == 3


class TestResolvePriority:
    def test_scenario_overrides_feature(self) -> None:
        config = PriorityConfig()
        result = resolve_priority(
            scenario_tags=["priority(1)"],
            feature_tags=["feature-priority(2)"],
            config=config,
        )
        assert result == 1

    def test_feature_priority_when_no_scenario_priority(self) -> None:
        config = PriorityConfig()
        result = resolve_priority(
            scenario_tags=["critical", "smoke"],
            feature_tags=["feature-priority(2)"],
            config=config,
        )
        assert result == 2

    def test_default_when_no_tags(self) -> None:
        config = PriorityConfig()
        result = resolve_priority(
            scenario_tags=["smoke"],
            feature_tags=["regression"],
            config=config,
        )
        assert result == 999

    def test_custom_default_priority(self) -> None:
        config = PriorityConfig(default_priority=100)
        result = resolve_priority(
            scenario_tags=[],
            feature_tags=[],
            config=config,
        )
        assert result == 100

    def test_scenario_priority_with_empty_feature_tags(self) -> None:
        config = PriorityConfig()
        result = resolve_priority(
            scenario_tags=["priority(5)"],
            feature_tags=[],
            config=config,
        )
        assert result == 5

    def test_feature_priority_with_empty_scenario_tags(self) -> None:
        config = PriorityConfig()
        result = resolve_priority(
            scenario_tags=[],
            feature_tags=["feature-priority(3)"],
            config=config,
        )
        assert result == 3

    def test_both_empty_uses_default(self) -> None:
        config = PriorityConfig(default_priority=42)
        result = resolve_priority(
            scenario_tags=[],
            feature_tags=[],
            config=config,
        )
        assert result == 42

    def test_scenario_priority_zero(self) -> None:
        config = PriorityConfig()
        result = resolve_priority(
            scenario_tags=["priority(0)"],
            feature_tags=["feature-priority(1)"],
            config=config,
        )
        assert result == 0

    def test_scenario_negative_overrides_feature(self) -> None:
        config = PriorityConfig()
        result = resolve_priority(
            scenario_tags=["priority(-10)"],
            feature_tags=["feature-priority(1)"],
            config=config,
        )
        assert result == -10

    def test_feature_priority_does_not_use_scenario_tag(self) -> None:
        config = PriorityConfig()
        result = resolve_priority(
            scenario_tags=[],
            feature_tags=["priority(1)"],
            config=config,
        )
        assert result == 999


class TestIsCritical:
    def test_has_critical_tag(self) -> None:
        assert is_critical(["critical", "smoke"]) is True

    def test_no_critical_tag(self) -> None:
        assert is_critical(["smoke", "regression"]) is False

    def test_empty_tags(self) -> None:
        assert is_critical([]) is False

    def test_only_critical_tag(self) -> None:
        assert is_critical(["critical"]) is True

    def test_custom_critical_tag(self) -> None:
        assert is_critical(["critico", "smoke"], critical_tag="critico") is True

    def test_custom_critical_tag_not_present(self) -> None:
        assert is_critical(["critical", "smoke"], critical_tag="critico") is False

    def test_case_sensitive(self) -> None:
        assert is_critical(["Critical"]) is False

    def test_partial_match_not_critical(self) -> None:
        assert is_critical(["critical-path"]) is False

    def test_at_prefix_critical_tag(self) -> None:
        assert is_critical(["@critical"]) is True

    def test_at_prefix_custom_critical_tag(self) -> None:
        assert is_critical(["@critico"], critical_tag="critico") is True

    def test_at_prefix_both_sides(self) -> None:
        assert is_critical(["@critical"], critical_tag="@critical") is True

    def test_whitespace_around_critical_tag(self) -> None:
        assert is_critical(["  critical  "]) is True
