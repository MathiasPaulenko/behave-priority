"""Tag priority parsing."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

from behave_priority.exceptions import PriorityParseError

if TYPE_CHECKING:
    from behave_priority.config import PriorityConfig

_PRIORITY_RE = re.compile(r"^priority\(\s*(-?\d+)\s*\)$")
_FEATURE_PRIORITY_RE = re.compile(r"^feature-priority\(\s*(-?\d+)\s*\)$")
_INT_RE = re.compile(r"^-?\d+$")


class Taggable(Protocol):
    """Protocol for objects with tags (Scenario, Feature)."""

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
        if tag.startswith("priority(") and tag.endswith(")"):
            inner = tag[len("priority(") : -1].strip()
            if not _INT_RE.match(inner):
                raise PriorityParseError(f"Invalid priority tag: {tag}")
    return None


def parse_feature_priority(tags: list[str]) -> int | None:
    """Parse @feature-priority(N) from a tag list.

    Same semantics as parse_priority but for feature-level tags.
    """
    for tag in tags:
        tag = tag.strip()
        if not tag.startswith("feature-priority("):
            continue
        match = _FEATURE_PRIORITY_RE.match(tag)
        if match:
            return int(match.group(1))
        if tag.startswith("feature-priority(") and tag.endswith(")"):
            inner = tag[len("feature-priority(") : -1].strip()
            if not _INT_RE.match(inner):
                raise PriorityParseError(
                    f"Invalid feature-priority tag: {tag}"
                )
    return None


def resolve_priority(
    scenario_tags: list[str],
    feature_tags: list[str],
    config: PriorityConfig,
) -> int:
    """Resolve effective priority for a scenario.

    Precedence: scenario > feature > default.
    """
    scenario_priority = parse_priority(scenario_tags)
    if scenario_priority is not None:
        return scenario_priority

    feature_priority = parse_feature_priority(feature_tags)
    if feature_priority is not None:
        return feature_priority

    return config.default_priority


def is_critical(tags: list[str], critical_tag: str = "critical") -> bool:
    """Check if a tag list contains the critical tag."""
    return critical_tag in tags
