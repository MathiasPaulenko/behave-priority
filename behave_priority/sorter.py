"""Reorders behave's feature and scenario lists by priority."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from behave_priority.parser import resolve_priority

if TYPE_CHECKING:
    from behave_priority.config import PriorityConfig


class ScenarioLike(Protocol):
    name: str
    tags: list[str]
    status: str
    duration: float


class FeatureLike(Protocol):
    name: str | None
    filename: str
    tags: list[str]
    scenarios: list[ScenarioLike]


class ScenarioSorter:
    """Reorders behave's feature and scenario lists by priority."""

    def __init__(self, config: PriorityConfig) -> None:
        self._config = config

    def sort(self, features: list[FeatureLike]) -> list[FeatureLike]:
        """Sort features and their scenarios by priority.

        Returns a new list of features. Each feature's scenarios list
        is reordered in-place.
        """
        for feature in features:
            sorted_scenarios = self._sort_scenarios(
                feature.scenarios, feature.tags
            )
            feature.scenarios = sorted_scenarios

            feature_obj: Any = feature
            run_items = getattr(feature_obj, "run_items", None)
            if run_items is not None:
                sorted_items = self._sort_scenarios(
                    run_items, feature.tags
                )
                feature_obj.run_items = sorted_items

        if self._config.order or self._config.reverse or self._config.priority_tag:
            features = sorted(features, key=self._feature_sort_key)

        return features

    def _sort_scenarios(
        self, scenarios: list[ScenarioLike], feature_tags: list[str]
    ) -> list[ScenarioLike]:
        """Sort scenarios within a feature by priority."""
        return sorted(
            scenarios,
            key=lambda s: self._sort_key(s.tags, feature_tags),
        )

    def _sort_key(
        self, scenario_tags: list[str], feature_tags: list[str]
    ) -> tuple[int, int]:
        """Compute sort key for a scenario."""
        priority = resolve_priority(scenario_tags, feature_tags, self._config)

        if self._config.priority_tag:
            tag = self._config.priority_tag.lstrip("@")
            primary = 0 if tag in scenario_tags else 1
        else:
            primary = 0

        secondary = -priority if self._config.reverse else priority

        return (primary, secondary)

    def _feature_sort_key(self, feature: FeatureLike) -> tuple[int, int]:
        """Compute sort key for a feature (based on its best scenario)."""
        if not feature.scenarios:
            return (1, self._config.default_priority)

        best = min(
            self._sort_key(s.tags, feature.tags)
            for s in feature.scenarios
        )
        return best
