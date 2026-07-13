"""Reorders behave's feature and scenario lists by priority."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from behave_priority.parser import resolve_priority

if TYPE_CHECKING:
    from behave_priority.config import PriorityConfig


class ScenarioLike(Protocol):
    """Protocol for scenario-like objects.

    Attributes:
        name: Display name of the scenario.
        tags: List of tag strings (without '@' prefix).
        status: Execution status (``"passed"``, ``"failed"``, etc.).
        duration: Execution time in seconds.
    """

    name: str
    tags: list[str]
    status: str
    duration: float


class FeatureLike(Protocol):
    """Protocol for feature-like objects.

    Attributes:
        name: Display name of the feature, or None.
        filename: Path to the feature file.
        tags: List of tag strings (without '@' prefix).
        scenarios: List of scenarios belonging to this feature.
    """

    name: str | None
    filename: str
    tags: list[str]
    scenarios: list[ScenarioLike]


class ScenarioSorter:
    """Reorders behave's feature and scenario lists by priority."""

    def __init__(self, config: PriorityConfig) -> None:
        """Initialize the sorter.

        Args:
            config: Configuration controlling sort behavior.
        """
        self._config = config

    def sort(self, features: list[FeatureLike]) -> list[FeatureLike]:
        """Sort features and their scenarios by priority.

        Each feature's ``scenarios`` list and ``run_items`` list (if present)
        are reordered in-place. The features list itself is also sorted
        when ordering is enabled.

        Args:
            features: List of features to sort.

        Returns:
            A new list of features sorted by priority.
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
        """Sort scenarios within a feature by priority.

        Args:
            scenarios: Scenarios to sort.
            feature_tags: Tags from the parent feature.

        Returns:
            A new list of scenarios sorted by priority.
        """
        return sorted(
            scenarios,
            key=lambda s: self._sort_key(s.tags, feature_tags),
        )

    def _sort_key(
        self, scenario_tags: list[str], feature_tags: list[str]
    ) -> tuple[int, int]:
        """Compute sort key for a scenario.

        Args:
            scenario_tags: Tags on the scenario.
            feature_tags: Tags from the parent feature.

        Returns:
            A tuple of (primary, secondary) sort keys.
        """
        priority = resolve_priority(scenario_tags, feature_tags, self._config)

        if self._config.priority_tag:
            tag = self._config.priority_tag.lstrip("@")
            primary = 0 if tag in scenario_tags else 1
        else:
            primary = 0

        secondary = -priority if self._config.reverse else priority

        return (primary, secondary)

    def _feature_sort_key(self, feature: FeatureLike) -> tuple[int, int]:
        """Compute sort key for a feature based on its best scenario.

        Args:
            feature: The feature to evaluate.

        Returns:
            A tuple of (primary, secondary) sort keys.
        """
        items: list[ScenarioLike] = getattr(feature, "run_items", None) or feature.scenarios
        if not items:
            return (1, self._config.default_priority)

        best = min(
            self._sort_key(s.tags, feature.tags)
            for s in items
        )
        return best
