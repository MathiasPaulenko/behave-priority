"""Unit tests for behave_priority.sorter."""

from __future__ import annotations

from dataclasses import dataclass, field

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
