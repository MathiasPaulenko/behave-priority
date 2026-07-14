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

        The sort is **stable**: scenarios with the same priority preserve
        their original relative order. This ensures that Scenario Outlines
        expanded by behave (which share the same tags and therefore the same
        priority) remain grouped together after sorting.

        When a feature's ``run_items`` contains ``Rule`` objects (Gherkin v6),
        each rule's inner ``run_items`` and ``scenarios`` are also sorted.

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
                sorted_items = self._sort_run_items(
                    run_items, feature.tags
                )
                feature_obj.run_items = sorted_items

        if self._config.order or self._config.reverse or self._config.priority_tag:
            features = sorted(features, key=self._feature_sort_key)

        return features

    def _sort_run_items(
        self, run_items: list[Any], feature_tags: list[str]
    ) -> list[Any]:
        """Sort run_items, recursing into Rule objects.

        Args:
            run_items: List of run items (Scenario, ScenarioOutline, or Rule).
            feature_tags: Tags from the parent feature.

        Returns:
            A new list of run items sorted by priority.
        """
        for item in run_items:
            if self._is_rule(item):
                rule_obj: Any = item
                rule_tags = getattr(rule_obj, "tags", [])
                inner_items = getattr(rule_obj, "run_items", None)
                if inner_items is not None:
                    rule_obj.run_items = self._sort_scenarios(
                        inner_items, feature_tags, rule_tags
                    )
                inner_scenarios = getattr(rule_obj, "scenarios", None)
                if inner_scenarios is not None:
                    rule_obj.scenarios = self._sort_scenarios(
                        inner_scenarios, feature_tags, rule_tags
                    )

        return sorted(
            run_items,
            key=lambda item: self._run_item_sort_key(item, feature_tags),
        )

    @staticmethod
    def _is_rule(item: Any) -> bool:
        """Check if a run item is a Rule object (Gherkin v6).

        Within ``feature.run_items``, only ``Rule`` objects have a
        ``run_items`` attribute. ``Scenario`` and ``ScenarioOutline``
        do not.

        Args:
            item: The run item to check.

        Returns:
            True if the item is a Rule (has ``run_items``).
        """
        return hasattr(item, "run_items")

    def _run_item_sort_key(
        self, item: Any, feature_tags: list[str]
    ) -> tuple[int, int]:
        """Compute sort key for a run item (Scenario or Rule).

        Args:
            item: The run item to evaluate.
            feature_tags: Tags from the parent feature.

        Returns:
            A tuple of (primary, secondary) sort keys.
        """
        if self._is_rule(item):
            rule_tags = getattr(item, "tags", [])
            inner_items: Any = (
                getattr(item, "run_items", None) or item.scenarios
            )
            if not inner_items:
                return (1, self._config.default_priority)
            return min(
                self._sort_key(s.tags, feature_tags, rule_tags)
                for s in inner_items
            )
        return self._sort_key(item.tags, feature_tags)

    def _sort_scenarios(
        self,
        scenarios: list[ScenarioLike],
        feature_tags: list[str],
        rule_tags: list[str] | None = None,
    ) -> list[ScenarioLike]:
        """Sort scenarios within a feature (or rule) by priority.

        Args:
            scenarios: Scenarios to sort.
            feature_tags: Tags from the parent feature.
            rule_tags: Tags from the parent rule (Gherkin v6), if any.

        Returns:
            A new list of scenarios sorted by priority.
        """
        return sorted(
            scenarios,
            key=lambda s: self._sort_key(s.tags, feature_tags, rule_tags),
        )

    def _sort_key(
        self,
        scenario_tags: list[str],
        feature_tags: list[str],
        rule_tags: list[str] | None = None,
    ) -> tuple[int, int]:
        """Compute sort key for a scenario.

        Args:
            scenario_tags: Tags on the scenario.
            feature_tags: Tags from the parent feature.
            rule_tags: Tags from the parent rule (Gherkin v6), if any.

        Returns:
            A tuple of (primary, secondary) sort keys.
        """
        priority = resolve_priority(
            scenario_tags, feature_tags, self._config, rule_tags
        )

        if self._config.priority_tag:
            tag = self._config.priority_tag.removeprefix("@")
            all_tags = list(scenario_tags)
            if rule_tags:
                all_tags.extend(rule_tags)
            all_tags.extend(feature_tags)
            normalized = {t.removeprefix("@").strip() for t in all_tags}
            primary = 0 if tag in normalized else 1
        else:
            primary = 0

        secondary = -priority if self._config.reverse else priority

        return (primary, secondary)

    def _feature_sort_key(self, feature: FeatureLike) -> tuple[int, int]:
        """Compute sort key for a feature based on its best run item.

        Handles both plain scenarios and Rule objects (Gherkin v6).

        Args:
            feature: The feature to evaluate.

        Returns:
            A tuple of (primary, secondary) sort keys.
        """
        items: Any = getattr(feature, "run_items", None)
        if items:
            best = min(
                self._run_item_sort_key(item, feature.tags)
                for item in items
            )
            return best
        scenarios = feature.scenarios
        if not scenarios:
            return (1, self._config.default_priority)
        return min(
            self._sort_key(s.tags, feature.tags)
            for s in scenarios
        )
