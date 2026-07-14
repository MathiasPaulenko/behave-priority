"""Unit tests for behave_priority.sorter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from behave_priority.config import PriorityConfig
from behave_priority.sorter import ScenarioSorter


@dataclass
class FakeScenario:
    name: str
    tags: list[str] = field(default_factory=list)
    status: str = "passed"
    duration: float = 0.0


@dataclass
class FakeFeature:
    name: str | None
    filename: str
    tags: list[str] = field(default_factory=list)
    scenarios: list[FakeScenario] = field(default_factory=list)
    run_items: list[Any] | None = None


@dataclass
class FakeRule:
    name: str
    tags: list[str] = field(default_factory=list)
    scenarios: list[FakeScenario] = field(default_factory=list)
    run_items: list[FakeScenario] | None = None


def make_feature(
    name: str,
    tags: list[str] | None = None,
    scenarios: list[FakeScenario] | None = None,
) -> FakeFeature:
    return FakeFeature(
        name=name,
        filename=f"features/{name.lower().replace(' ', '_')}.feature",
        tags=tags or [],
        scenarios=scenarios or [],
    )


class TestSortScenarios:
    def test_no_priority_tags_preserves_order(self) -> None:
        config = PriorityConfig()
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("first")
        s2 = FakeScenario("second")
        s3 = FakeScenario("third")
        feature = make_feature("F", scenarios=[s1, s2, s3])
        sorter.sort([feature])
        assert feature.scenarios == [s1, s2, s3]

    def test_sorts_by_scenario_priority(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("low", tags=["priority(3)"])
        s2 = FakeScenario("high", tags=["priority(1)"])
        s3 = FakeScenario("mid", tags=["priority(2)"])
        feature = make_feature("F", scenarios=[s1, s2, s3])
        sorter.sort([feature])
        assert feature.scenarios == [s2, s3, s1]

    def test_feature_priority_fallback(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("no_tag")
        s2 = FakeScenario("explicit", tags=["priority(1)"])
        feature = make_feature("F", tags=["feature-priority(5)"], scenarios=[s1, s2])
        sorter.sort([feature])
        assert feature.scenarios[0] == s2
        assert feature.scenarios[1] == s1

    def test_default_priority_for_untagged(self) -> None:
        config = PriorityConfig(order=True, default_priority=100)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("untagged")
        s2 = FakeScenario("tagged", tags=["priority(50)"])
        feature = make_feature("F", scenarios=[s1, s2])
        sorter.sort([feature])
        assert feature.scenarios == [s2, s1]

    def test_reverse_sort(self) -> None:
        config = PriorityConfig(order=True, reverse=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("low", tags=["priority(1)"])
        s2 = FakeScenario("high", tags=["priority(3)"])
        feature = make_feature("F", scenarios=[s1, s2])
        sorter.sort([feature])
        assert feature.scenarios == [s2, s1]

    def test_priority_tag_grouping(self) -> None:
        config = PriorityConfig(priority_tag="smoke")
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("normal")
        s2 = FakeScenario("smoke", tags=["smoke"])
        s3 = FakeScenario("normal2")
        s4 = FakeScenario("smoke2", tags=["smoke"])
        feature = make_feature("F", scenarios=[s1, s2, s3, s4])
        sorter.sort([feature])
        smoke_names = [s.name for s in feature.scenarios if "smoke" in s.tags]
        normal_names = [s.name for s in feature.scenarios if "smoke" not in s.tags]
        assert len(smoke_names) == 2
        assert len(normal_names) == 2
        first_smoke_idx = next(
            i for i, s in enumerate(feature.scenarios) if "smoke" in s.tags
        )
        first_normal_idx = next(
            i for i, s in enumerate(feature.scenarios) if "smoke" not in s.tags
        )
        assert first_smoke_idx < first_normal_idx

    def test_priority_tag_with_at_prefix(self) -> None:
        config = PriorityConfig(priority_tag="@smoke")
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("normal")
        s2 = FakeScenario("smoke", tags=["smoke"])
        feature = make_feature("F", scenarios=[s1, s2])
        sorter.sort([feature])
        assert feature.scenarios[0] == s2

    def test_stable_sort_equal_priorities(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("first", tags=["priority(1)"])
        s2 = FakeScenario("second", tags=["priority(1)"])
        s3 = FakeScenario("third", tags=["priority(1)"])
        feature = make_feature("F", scenarios=[s1, s2, s3])
        sorter.sort([feature])
        assert feature.scenarios == [s1, s2, s3]

    def test_empty_scenarios(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        feature = make_feature("F", scenarios=[])
        result = sorter.sort([feature])
        assert result == [feature]
        assert feature.scenarios == []

    def test_single_scenario(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s = FakeScenario("only", tags=["priority(1)"])
        feature = make_feature("F", scenarios=[s])
        sorter.sort([feature])
        assert feature.scenarios == [s]

    def test_negative_priorities(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("normal", tags=["priority(5)"])
        s2 = FakeScenario("urgent", tags=["priority(-10)"])
        feature = make_feature("F", scenarios=[s1, s2])
        sorter.sort([feature])
        assert feature.scenarios == [s2, s1]

    def test_zero_priority(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("zero", tags=["priority(0)"])
        s2 = FakeScenario("one", tags=["priority(1)"])
        feature = make_feature("F", scenarios=[s2, s1])
        sorter.sort([feature])
        assert feature.scenarios == [s1, s2]


class TestSortFeatures:
    def test_features_not_sorted_without_order(self) -> None:
        config = PriorityConfig()
        sorter = ScenarioSorter(config)
        f1 = make_feature("Alpha", scenarios=[FakeScenario("a", tags=["priority(1)"])])
        f2 = make_feature("Beta", scenarios=[FakeScenario("b", tags=["priority(0)"])])
        result = sorter.sort([f1, f2])
        assert result == [f1, f2]

    def test_features_sorted_by_best_scenario(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        f1 = make_feature(
            "Alpha",
            scenarios=[
                FakeScenario("a1", tags=["priority(3)"]),
                FakeScenario("a2", tags=["priority(5)"]),
            ],
        )
        f2 = make_feature(
            "Beta",
            scenarios=[
                FakeScenario("b1", tags=["priority(1)"]),
                FakeScenario("b2", tags=["priority(2)"]),
            ],
        )
        result = sorter.sort([f1, f2])
        assert result == [f2, f1]

    def test_features_sorted_reverse(self) -> None:
        config = PriorityConfig(order=True, reverse=True)
        sorter = ScenarioSorter(config)
        f1 = make_feature(
            "Alpha",
            scenarios=[FakeScenario("a", tags=["priority(1)"])],
        )
        f2 = make_feature(
            "Beta",
            scenarios=[FakeScenario("b", tags=["priority(3)"])],
        )
        result = sorter.sort([f1, f2])
        assert result == [f2, f1]

    def test_features_with_priority_tag(self) -> None:
        config = PriorityConfig(priority_tag="smoke")
        sorter = ScenarioSorter(config)
        f1 = make_feature(
            "NoSmoke",
            scenarios=[FakeScenario("a", tags=["priority(1)"])],
        )
        f2 = make_feature(
            "HasSmoke",
            scenarios=[FakeScenario("b", tags=["smoke", "priority(5)"])],
        )
        result = sorter.sort([f1, f2])
        assert result[0] == f2

    def test_empty_feature_list(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        result = sorter.sort([])
        assert result == []

    def test_feature_with_no_scenarios(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        f1 = make_feature("Empty", scenarios=[])
        f2 = make_feature(
            "HasScenario",
            scenarios=[FakeScenario("s", tags=["priority(1)"])],
        )
        result = sorter.sort([f1, f2])
        assert result[0] == f2
        assert result[1] == f1

    def test_feature_priority_tag_affects_sorting(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        f1 = make_feature(
            "LowFeature",
            tags=["feature-priority(5)"],
            scenarios=[FakeScenario("a")],
        )
        f2 = make_feature(
            "HighFeature",
            tags=["feature-priority(1)"],
            scenarios=[FakeScenario("b")],
        )
        result = sorter.sort([f1, f2])
        assert result == [f2, f1]

    def test_mixed_feature_and_scenario_priority(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        f1 = make_feature(
            "FeatureA",
            tags=["feature-priority(3)"],
            scenarios=[
                FakeScenario("a1", tags=["priority(1)"]),
                FakeScenario("a2"),
            ],
        )
        f2 = make_feature(
            "FeatureB",
            tags=["feature-priority(1)"],
            scenarios=[FakeScenario("b1")],
        )
        result = sorter.sort([f1, f2])
        assert result[0] == f1

    def test_returns_new_list(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        f1 = make_feature("F", scenarios=[FakeScenario("s")])
        original = [f1]
        result = sorter.sort(original)
        assert result is not original


class TestSortKey:
    def test_sort_key_with_priority(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        key = sorter._sort_key(["priority(1)"], [])
        assert key == (0, 1)

    def test_sort_key_no_priority(self) -> None:
        config = PriorityConfig(order=True, default_priority=500)
        sorter = ScenarioSorter(config)
        key = sorter._sort_key([], [])
        assert key == (0, 500)

    def test_sort_key_with_priority_tag_present(self) -> None:
        config = PriorityConfig(priority_tag="smoke")
        sorter = ScenarioSorter(config)
        key = sorter._sort_key(["smoke", "priority(3)"], [])
        assert key == (0, 3)

    def test_sort_key_with_priority_tag_absent(self) -> None:
        config = PriorityConfig(priority_tag="smoke")
        sorter = ScenarioSorter(config)
        key = sorter._sort_key(["priority(3)"], [])
        assert key == (1, 3)

    def test_sort_key_reverse(self) -> None:
        config = PriorityConfig(order=True, reverse=True)
        sorter = ScenarioSorter(config)
        key = sorter._sort_key(["priority(1)"], [])
        assert key == (0, -1)

    def test_sort_key_feature_fallback(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        key = sorter._sort_key([], ["feature-priority(2)"])
        assert key == (0, 2)

    def test_sort_key_negative_priority(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        key = sorter._sort_key(["priority(-5)"], [])
        assert key == (0, -5)


class TestFeatureSortKey:
    def test_empty_feature(self) -> None:
        config = PriorityConfig(order=True, default_priority=100)
        sorter = ScenarioSorter(config)
        feature = make_feature("Empty", scenarios=[])
        key = sorter._feature_sort_key(feature)
        assert key == (1, 100)

    def test_best_scenario_priority(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        feature = make_feature(
            "F",
            scenarios=[
                FakeScenario("a", tags=["priority(5)"]),
                FakeScenario("b", tags=["priority(1)"]),
                FakeScenario("c", tags=["priority(3)"]),
            ],
        )
        key = sorter._feature_sort_key(feature)
        assert key == (0, 1)

    def test_with_priority_tag(self) -> None:
        config = PriorityConfig(priority_tag="smoke")
        sorter = ScenarioSorter(config)
        feature = make_feature(
            "F",
            scenarios=[
                FakeScenario("a", tags=["priority(1)"]),
                FakeScenario("b", tags=["smoke", "priority(5)"]),
            ],
        )
        key = sorter._feature_sort_key(feature)
        assert key[0] == 0

    def test_no_smoke_in_feature(self) -> None:
        config = PriorityConfig(priority_tag="smoke")
        sorter = ScenarioSorter(config)
        feature = make_feature(
            "F",
            scenarios=[FakeScenario("a", tags=["priority(1)"])],
        )
        key = sorter._feature_sort_key(feature)
        assert key[0] == 1


class TestSortWithRunItems:
    def test_run_items_sorted_when_present(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("low", tags=["priority(3)"])
        s2 = FakeScenario("high", tags=["priority(1)"])
        s3 = FakeScenario("mid", tags=["priority(2)"])
        feature = FakeFeature(
            name="F",
            filename="f.feature",
            scenarios=[s1, s2, s3],
            run_items=[s1, s2, s3],
        )
        sorter.sort([feature])
        assert feature.run_items == [s2, s3, s1]
        assert feature.scenarios == [s2, s3, s1]

    def test_run_items_none_falls_back_to_scenarios(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("low", tags=["priority(3)"])
        s2 = FakeScenario("high", tags=["priority(1)"])
        feature = make_feature("F", scenarios=[s1, s2])
        sorter.sort([feature])
        assert feature.run_items is None
        assert feature.scenarios == [s2, s1]

    def test_run_items_different_from_scenarios(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("low", tags=["priority(3)"])
        s2 = FakeScenario("high", tags=["priority(1)"])
        s3 = FakeScenario("mid", tags=["priority(2)"])
        feature = FakeFeature(
            name="F",
            filename="f.feature",
            scenarios=[s1, s2],
            run_items=[s1, s2, s3],
        )
        sorter.sort([feature])
        assert feature.run_items == [s2, s3, s1]
        assert feature.scenarios == [s2, s1]

    def test_feature_sort_key_uses_run_items(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("low", tags=["priority(5)"])
        s2 = FakeScenario("high", tags=["priority(1)"])
        feature = FakeFeature(
            name="F",
            filename="f.feature",
            scenarios=[s1],
            run_items=[s1, s2],
        )
        key = sorter._feature_sort_key(feature)
        assert key == (0, 1)


class TestSortWithAtPrefix:
    def test_priority_tag_with_at_prefix_in_scenario_tags(self) -> None:
        config = PriorityConfig(priority_tag="smoke")
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("normal")
        s2 = FakeScenario("smoke", tags=["@smoke"])
        feature = make_feature("F", scenarios=[s1, s2])
        sorter.sort([feature])
        assert feature.scenarios[0] == s2

    def test_priority_tag_with_at_prefix_in_config(self) -> None:
        config = PriorityConfig(priority_tag="@smoke")
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("normal")
        s2 = FakeScenario("smoke", tags=["smoke"])
        feature = make_feature("F", scenarios=[s1, s2])
        sorter.sort([feature])
        assert feature.scenarios[0] == s2

    def test_both_at_prefixed(self) -> None:
        config = PriorityConfig(priority_tag="@smoke")
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("normal")
        s2 = FakeScenario("smoke", tags=["@smoke"])
        feature = make_feature("F", scenarios=[s1, s2])
        sorter.sort([feature])
        assert feature.scenarios[0] == s2


class TestRealWorldScenarios:
    def test_multiple_features_mixed_priorities(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        f1 = make_feature(
            "Auth",
            scenarios=[
                FakeScenario("login", tags=["priority(2)"]),
                FakeScenario("logout", tags=["priority(5)"]),
            ],
        )
        f2 = make_feature(
            "Payment",
            scenarios=[
                FakeScenario("checkout", tags=["priority(1)"]),
                FakeScenario("refund", tags=["priority(3)"]),
            ],
        )
        f3 = make_feature(
            "Profile",
            scenarios=[
                FakeScenario("view", tags=["priority(4)"]),
                FakeScenario("edit", tags=["priority(6)"]),
            ],
        )
        result = sorter.sort([f3, f1, f2])
        assert result[0] == f2
        assert result[1] == f1
        assert result[2] == f3
        assert [s.name for s in f1.scenarios] == ["login", "logout"]
        assert [s.name for s in f2.scenarios] == ["checkout", "refund"]
        assert [s.name for s in f3.scenarios] == ["view", "edit"]

    def test_smoke_first_then_priority_order(self) -> None:
        config = PriorityConfig(order=True, priority_tag="smoke")
        sorter = ScenarioSorter(config)
        f1 = make_feature(
            "FeatureA",
            scenarios=[
                FakeScenario("smoke_test", tags=["smoke", "priority(5)"]),
                FakeScenario("unit_test", tags=["priority(1)"]),
            ],
        )
        f2 = make_feature(
            "FeatureB",
            scenarios=[
                FakeScenario("integration", tags=["priority(2)"]),
            ],
        )
        result = sorter.sort([f2, f1])
        assert result[0] == f1
        assert f1.scenarios[0].name == "smoke_test"

    def test_all_same_priority_preserves_order(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        scenarios = [
            FakeScenario(f"s{i}", tags=["priority(1)"]) for i in range(10)
        ]
        feature = make_feature("F", scenarios=scenarios)
        sorter.sort([feature])
        assert [s.name for s in feature.scenarios] == [f"s{i}" for i in range(10)]

    def test_feature_with_feature_priority_and_scenario_override(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        f1 = make_feature(
            "HighFeature",
            tags=["feature-priority(1)"],
            scenarios=[
                FakeScenario("override", tags=["priority(10)"]),
                FakeScenario("inherits", tags=[]),
            ],
        )
        f2 = make_feature(
            "LowFeature",
            tags=["feature-priority(5)"],
            scenarios=[FakeScenario("low", tags=["priority(3)"])],
        )
        result = sorter.sort([f2, f1])
        assert result[0] == f1
        assert f1.scenarios[0].name == "inherits"
        assert f1.scenarios[1].name == "override"

    def test_empty_features_and_empty_scenarios_mixed(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        f1 = make_feature("Empty", scenarios=[])
        f2 = make_feature(
            "HasOne",
            scenarios=[FakeScenario("s", tags=["priority(1)"])],
        )
        f3 = make_feature("AlsoEmpty", scenarios=[])
        result = sorter.sort([f1, f2, f3])
        assert result[0] == f2


class TestSortStability:
    def test_same_priority_preserves_order(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("first")
        s2 = FakeScenario("second")
        s3 = FakeScenario("third")
        feature = make_feature("F", scenarios=[s1, s2, s3])
        sorter.sort([feature])
        assert feature.scenarios == [s1, s2, s3]

    def test_outline_examples_stay_grouped(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        outline_a = FakeScenario("Login outline <row 1>")
        outline_b = FakeScenario("Login outline <row 2>")
        outline_c = FakeScenario("Login outline <row 3>")
        high = FakeScenario("Smoke test", tags=["priority(1)"])
        low = FakeScenario("Regression", tags=["priority(5)"])
        feature = make_feature(
            "F", scenarios=[outline_a, outline_b, outline_c, high, low]
        )
        sorter.sort([feature])
        names = [s.name for s in feature.scenarios]
        assert names == [
            "Smoke test",
            "Regression",
            "Login outline <row 1>",
            "Login outline <row 2>",
            "Login outline <row 3>",
        ]

    def test_outline_with_same_tag_stays_grouped(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        outline_a = FakeScenario("Outline <a>", tags=["priority(2)"])
        outline_b = FakeScenario("Outline <b>", tags=["priority(2)"])
        outline_c = FakeScenario("Outline <c>", tags=["priority(2)"])
        high = FakeScenario("High", tags=["priority(1)"])
        feature = make_feature(
            "F", scenarios=[outline_a, outline_b, outline_c, high]
        )
        sorter.sort([feature])
        names = [s.name for s in feature.scenarios]
        assert names == ["High", "Outline <a>", "Outline <b>", "Outline <c>"]

    def test_two_outlines_same_priority_stay_grouped(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        o1a = FakeScenario("Outline1 <a>")
        o1b = FakeScenario("Outline1 <b>")
        o2a = FakeScenario("Outline2 <a>")
        o2b = FakeScenario("Outline2 <b>")
        feature = make_feature(
            "F", scenarios=[o1a, o1b, o2a, o2b]
        )
        sorter.sort([feature])
        names = [s.name for s in feature.scenarios]
        assert names == ["Outline1 <a>", "Outline1 <b>", "Outline2 <a>", "Outline2 <b>"]

    def test_stability_with_mixed_priorities(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        a1 = FakeScenario("A1", tags=["priority(1)"])
        b1 = FakeScenario("B1", tags=["priority(2)"])
        b2 = FakeScenario("B2", tags=["priority(2)"])
        b3 = FakeScenario("B3", tags=["priority(2)"])
        a2 = FakeScenario("A2", tags=["priority(1)"])
        feature = make_feature(
            "F", scenarios=[b1, b2, a1, b3, a2]
        )
        sorter.sort([feature])
        names = [s.name for s in feature.scenarios]
        assert names == ["A1", "A2", "B1", "B2", "B3"]


class TestRuleSupport:
    def test_rule_inner_scenarios_sorted(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("low", tags=["priority(5)"])
        s2 = FakeScenario("high", tags=["priority(1)"])
        rule = FakeRule("R1", run_items=[s1, s2], scenarios=[s1, s2])
        feature = FakeFeature("F", "f.feature", run_items=[rule])
        sorter.sort([feature])
        rule_items = rule.run_items or []
        assert [s.name for s in rule_items] == ["high", "low"]

    def test_rule_tags_provide_priority(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("inherits_rule")
        s2 = FakeScenario("explicit", tags=["priority(1)"])
        rule = FakeRule("R", tags=["priority(3)"], run_items=[s1, s2], scenarios=[s1, s2])
        feature = FakeFeature("F", "f.feature", run_items=[rule])
        sorter.sort([feature])
        rule_items = rule.run_items or []
        assert [s.name for s in rule_items] == ["explicit", "inherits_rule"]

    def test_rule_sorted_among_scenarios(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        standalone = FakeScenario("standalone_low", tags=["priority(9)"])
        rule_s = FakeScenario("rule_high", tags=["priority(1)"])
        rule = FakeRule("R", run_items=[rule_s], scenarios=[rule_s])
        feature = FakeFeature(
            "F", "f.feature",
            run_items=[standalone, rule],
            scenarios=[standalone, rule_s],
        )
        sorter.sort([feature])
        items = feature.run_items or []
        assert items[0] is rule
        assert items[1] is standalone

    def test_feature_with_rules_and_scenarios(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("s1", tags=["priority(3)"])
        s2 = FakeScenario("s2", tags=["priority(1)"])
        rule1 = FakeRule("R1", run_items=[s1], scenarios=[s1])
        rule2 = FakeRule("R2", run_items=[s2], scenarios=[s2])
        feature = FakeFeature(
            "F", "f.feature",
            run_items=[rule1, rule2],
            scenarios=[s1, s2],
        )
        sorter.sort([feature])
        items = feature.run_items or []
        assert items[0] is rule2
        assert items[1] is rule1

    def test_rule_with_no_run_items(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        rule = FakeRule("R", run_items=None, scenarios=[])
        feature = FakeFeature("F", "f.feature", run_items=[rule])
        sorter.sort([feature])

    def test_rule_scenarios_also_sorted(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        s1 = FakeScenario("low", tags=["priority(5)"])
        s2 = FakeScenario("high", tags=["priority(1)"])
        rule = FakeRule("R", scenarios=[s1, s2], run_items=None)
        feature = FakeFeature("F", "f.feature", run_items=[rule])
        sorter.sort([feature])
        assert [s.name for s in rule.scenarios] == ["high", "low"]

    def test_mixed_rule_and_scenario_in_run_items(self) -> None:
        config = PriorityConfig(order=True)
        sorter = ScenarioSorter(config)
        plain = FakeScenario("plain", tags=["priority(2)"])
        rule_s = FakeScenario("rule_s", tags=["priority(1)"])
        rule = FakeRule("R", run_items=[rule_s], scenarios=[rule_s])
        feature = FakeFeature(
            "F", "f.feature",
            run_items=[plain, rule],
            scenarios=[plain, rule_s],
        )
        sorter.sort([feature])
        items = feature.run_items or []
        assert items[0] is rule
        assert items[1] is plain
