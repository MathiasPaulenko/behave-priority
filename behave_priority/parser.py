"""Tag priority parsing."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

from behave_priority.exceptions import PriorityParseError

if TYPE_CHECKING:
    from behave_priority.config import PriorityConfig

_PRIORITY_RE = re.compile(r"^priority\(\s*(-?\d+)\s*\)$")
_FEATURE_PRIORITY_RE = re.compile(r"^feature-priority\(\s*(-?\d+)\s*\)$")


class Taggable(Protocol):
    """Protocol for objects with tags (Scenario, Feature).

    Attributes:
        tags: List of tag strings as behave stores them (without '@' prefix).
    """

    tags: list[str]


def parse_priority(tags: list[str]) -> int | None:
    """Parse @priority(N) from a tag list.

    Args:
        tags: List of tag strings (without '@' prefix, as behave stores them).

    Returns:
        Priority integer, or None if no priority tag found.

    Raises:
        PriorityParseError: If a priority tag exists but has invalid syntax.
    """
    for tag in tags:
        tag = tag.strip()
        if not tag.startswith("priority("):
            continue
        match = _PRIORITY_RE.match(tag)
        if match:
            return int(match.group(1))
        raise PriorityParseError(f"Invalid priority tag: {tag}")
    return None


def parse_feature_priority(tags: list[str]) -> int | None:
    """Parse @feature-priority(N) from a tag list.

    Same semantics as parse_priority but for feature-level tags.

    Args:
        tags: List of tag strings (without '@' prefix, as behave stores them).

    Returns:
        Priority integer, or None if no feature-priority tag found.

    Raises:
        PriorityParseError: If a feature-priority tag exists but has invalid
            syntax.
    """
    for tag in tags:
        tag = tag.strip()
        if not tag.startswith("feature-priority("):
            continue
        match = _FEATURE_PRIORITY_RE.match(tag)
        if match:
            return int(match.group(1))
        raise PriorityParseError(f"Invalid feature-priority tag: {tag}")
    return None


def resolve_priority(
    scenario_tags: list[str],
    feature_tags: list[str],
    config: PriorityConfig,
) -> int:
    """Resolve effective priority for a scenario.

    Precedence: scenario > feature > default.

    Args:
        scenario_tags: Tags on the scenario (without '@' prefix).
        feature_tags: Tags on the parent feature (without '@' prefix).
        config: Configuration containing the default priority fallback.

    Returns:
        The effective priority integer for the scenario.
    """
    scenario_priority = parse_priority(scenario_tags)
    if scenario_priority is not None:
        return scenario_priority

    feature_priority = parse_feature_priority(feature_tags)
    if feature_priority is not None:
        return feature_priority

    return config.default_priority


def is_critical(tags: list[str], critical_tag: str = "critical") -> bool:
    """Check if a tag list contains the critical tag.

    Both the tags and ``critical_tag`` are normalized by stripping leading
    '@' characters and whitespace before comparison.

    Args:
        tags: List of tag strings to search.
        critical_tag: The tag name that marks a scenario as critical.
            Defaults to ``"critical"``.

    Returns:
        True if the critical tag is present in the tag list.
    """
    normalized = {t.lstrip("@").strip() for t in tags}
    return critical_tag.lstrip("@").strip() in normalized
