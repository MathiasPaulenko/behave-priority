"""Unit tests for behave_priority.config."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from behave_priority.config import PriorityConfig


class TestDefaults:
    def test_order_default_false(self) -> None:
        config = PriorityConfig()
        assert config.order is False

    def test_reverse_default_false(self) -> None:
        config = PriorityConfig()
        assert config.reverse is False

    def test_priority_tag_default_none(self) -> None:
        config = PriorityConfig()
        assert config.priority_tag is None

    def test_stop_after_failures_default_none(self) -> None:
        config = PriorityConfig()
        assert config.stop_after_failures is None

    def test_stop_on_critical_default_false(self) -> None:
        config = PriorityConfig()
        assert config.stop_on_critical is False

    def test_critical_tag_default(self) -> None:
        config = PriorityConfig()
        assert config.critical_tag == "critical"

    def test_priority_tag_pattern_default(self) -> None:
        config = PriorityConfig()
        assert config.priority_tag_pattern == "priority({n})"

    def test_feature_priority_tag_pattern_default(self) -> None:
        config = PriorityConfig()
        assert config.feature_priority_tag_pattern == "feature-priority({n})"

    def test_default_priority_default_999(self) -> None:
        config = PriorityConfig()
        assert config.default_priority == 999

    def test_report_default_false(self) -> None:
        config = PriorityConfig()
        assert config.report is False


class TestKwargs:
    def test_order_true(self) -> None:
        config = PriorityConfig(order=True)
        assert config.order is True

    def test_reverse_true(self) -> None:
        config = PriorityConfig(reverse=True)
        assert config.reverse is True

    def test_priority_tag_set(self) -> None:
        config = PriorityConfig(priority_tag="critical")
        assert config.priority_tag == "critical"

    def test_priority_tag_with_at_prefix(self) -> None:
        config = PriorityConfig(priority_tag="@critical")
        assert config.priority_tag == "@critical"

    def test_stop_after_failures_set(self) -> None:
        config = PriorityConfig(stop_after_failures=3)
        assert config.stop_after_failures == 3

    def test_stop_after_failures_zero(self) -> None:
        config = PriorityConfig(stop_after_failures=0)
        assert config.stop_after_failures == 0

    def test_stop_after_failures_negative(self) -> None:
        config = PriorityConfig(stop_after_failures=-1)
        assert config.stop_after_failures == -1

    def test_stop_on_critical_true(self) -> None:
        config = PriorityConfig(stop_on_critical=True)
        assert config.stop_on_critical is True

    def test_critical_tag_custom(self) -> None:
        config = PriorityConfig(critical_tag="critico")
        assert config.critical_tag == "critico"

    def test_default_priority_custom(self) -> None:
        config = PriorityConfig(default_priority=100)
        assert config.default_priority == 100

    def test_default_priority_zero(self) -> None:
        config = PriorityConfig(default_priority=0)
        assert config.default_priority == 0

    def test_default_priority_negative(self) -> None:
        config = PriorityConfig(default_priority=-5)
        assert config.default_priority == -5

    def test_report_true(self) -> None:
        config = PriorityConfig(report=True)
        assert config.report is True

    def test_all_kwargs_together(self) -> None:
        config = PriorityConfig(
            order=True,
            reverse=True,
            priority_tag="smoke",
            stop_after_failures=5,
            stop_on_critical=True,
            critical_tag="critico",
            priority_tag_pattern="prio({n})",
            feature_priority_tag_pattern="fprio({n})",
            default_priority=500,
            report=True,
        )
        assert config.order is True
        assert config.reverse is True
        assert config.priority_tag == "smoke"
        assert config.stop_after_failures == 5
        assert config.stop_on_critical is True
        assert config.critical_tag == "critico"
        assert config.priority_tag_pattern == "prio({n})"
        assert config.feature_priority_tag_pattern == "fprio({n})"
        assert config.default_priority == 500
        assert config.report is True


class TestImmutability:
    def test_frozen_setattr_raises(self) -> None:
        config = PriorityConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.order = True  # type: ignore[misc]

    def test_frozen_delattr_raises(self) -> None:
        config = PriorityConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            del config.order  # type: ignore[misc]

    def test_cannot_add_new_attribute(self) -> None:
        config = PriorityConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.new_field = 42  # type: ignore[attr-defined]

    def test_slots_no_dict(self) -> None:
        config = PriorityConfig()
        assert not hasattr(config, "__dict__")


class TestEquality:
    def test_same_config_equal(self) -> None:
        c1 = PriorityConfig(order=True, stop_after_failures=3)
        c2 = PriorityConfig(order=True, stop_after_failures=3)
        assert c1 == c2

    def test_different_config_not_equal(self) -> None:
        c1 = PriorityConfig(order=True)
        c2 = PriorityConfig(order=False)
        assert c1 != c2

    def test_default_configs_equal(self) -> None:
        c1 = PriorityConfig()
        c2 = PriorityConfig()
        assert c1 == c2


class TestFields:
    def test_has_10_fields(self) -> None:
        fields = dataclasses.fields(PriorityConfig)
        assert len(fields) == 10

    def test_field_names(self) -> None:
        fields = dataclasses.fields(PriorityConfig)
        names = {f.name for f in fields}
        expected = {
            "order",
            "reverse",
            "priority_tag",
            "stop_after_failures",
            "stop_on_critical",
            "critical_tag",
            "priority_tag_pattern",
            "feature_priority_tag_pattern",
            "default_priority",
            "report",
        }
        assert names == expected

    def test_all_fields_have_types(self) -> None:
        fields = dataclasses.fields(PriorityConfig)
        for f in fields:
            assert f.type is not None

    def test_asdict(self) -> None:
        config = PriorityConfig(order=True, stop_after_failures=3)
        d = dataclasses.asdict(config)
        assert d["order"] is True
        assert d["stop_after_failures"] == 3
        assert d["default_priority"] == 999

    def test_asdict_returns_all_fields(self) -> None:
        config = PriorityConfig()
        d: dict[str, Any] = dataclasses.asdict(config)
        assert len(d) == 10
