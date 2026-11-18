"""Tag priority parsing."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

from behave_priority.exceptions import PriorityParseError

if TYPE_CHECKING:
    from behave_priority.config import PriorityConfig

_PRIORITY_RE = re.compile(r"^priority\(\s*([+-]?\d+)\s*\)$")
_FEATURE_PRIORITY_RE = re.compile(r"^feature-priority\(\s*([+-]?\d+)\s*\)$")


def _normalize_tag(tag: str) -> str:
    """Normalize a tag for comparison.

    Strips surrounding whitespace and a leading ``@`` prefix so that
    ``" @critical "`` and ``"critical"`` compare equal.

    Args:
        tag: The raw tag string.

    Returns:
        The normalized tag string.

    Raises:
        TypeError: If ``tag`` is not a string.
    """
    if not isinstance(tag, str):
        raise TypeError(f"tag must be a string, got {type(tag).__name__}")
    return tag.strip().removeprefix("@").strip()


def _parse_int(value: str, tag: str, *, kind: str = "priority") -> int:
    """Convert a matched priority value to int.

    ``int()`` raises ``ValueError`` for digit strings that exceed
    ``sys.get_int_max_str_digits()``; it is converted here into a
    ``PriorityParseError`` so callers get a consistent exception type.

    Args:
        value: The regex capture containing the digits.
        tag: The full tag string, for the error message.
        kind: Tag kind used in the error message.

    Returns:
        The parsed integer.

    Raises:
        PriorityParseError: If the value cannot be converted.
    """
    try:
        return int(value)
    except ValueError:
        raise PriorityParseError(f"Invalid {kind} tag: {tag}") from None


def _check_tags(tags: Iterable[str]) -> None:
    """Reject tag arguments that would silently misbehave.

    A plain ``str`` is iterable over its characters, so passing one
    instead of a list would iterate character-by-character and always
    fail to match — a silent wrong answer.

    Args:
        tags: The value passed as a tag collection.

    Raises:
        TypeError: If ``tags`` is a string or not iterable.
    """
    if isinstance(tags, str) or not isinstance(tags, Iterable):
        raise TypeError(f"tags must be an iterable of strings, got {type(tags).__name__}")


def parse_priority(tags: list[str]) -> int | None:
    """Parse @priority(N) from a tag list.

    Args:
        tags: List of tag strings (without '@' prefix, as behave stores them).

    Returns:
        Priority integer, or None if no priority tag found.

    Raises:
        PriorityParseError: If a priority tag exists but has invalid syntax.
        TypeError: If ``tags`` is not an iterable of strings.
    """
    _check_tags(tags)
    found: int | None = None
    for tag in tags:
        tag = _normalize_tag(tag)
        if not tag.startswith("priority("):
            continue
        match = _PRIORITY_RE.match(tag)
        if match:
            value = _parse_int(match.group(1), tag)
            found = value if found is None else min(found, value)
            continue
        raise PriorityParseError(f"Invalid priority tag: {tag}")
    return found


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
        TypeError: If ``tags`` is not an iterable of strings.
    """
    _check_tags(tags)
    found: int | None = None
    for tag in tags:
        tag = _normalize_tag(tag)
        if not tag.startswith("feature-priority("):
            continue
        match = _FEATURE_PRIORITY_RE.match(tag)
        if match:
            value = _parse_int(match.group(1), tag, kind="feature-priority")
            found = value if found is None else min(found, value)
            continue
        raise PriorityParseError(f"Invalid feature-priority tag: {tag}")
    return found


def resolve_priority(
    scenario_tags: list[str],
    feature_tags: list[str],
    config: PriorityConfig,
    rule_tags: list[str] | None = None,
) -> int:
    """Resolve effective priority for a scenario.

    Precedence: scenario > rule > feature > default.

    Args:
        scenario_tags: Tags on the scenario (without '@' prefix).
        feature_tags: Tags on the parent feature (without '@' prefix).
        config: Configuration containing the default priority fallback.
        rule_tags: Tags on the parent rule (Gherkin v6), if any.

    Returns:
        The effective priority integer for the scenario.
    """
    scenario_priority = parse_priority(scenario_tags)
    if scenario_priority is not None:
        return scenario_priority

    if rule_tags:
        rule_priority = parse_priority(rule_tags)
        if rule_priority is not None:
            return rule_priority

    feature_priority = parse_feature_priority(feature_tags)
    if feature_priority is not None:
        return feature_priority

    return config.default_priority


def is_critical(tags: list[str], critical_tag: str = "critical") -> bool:
    """Check if a tag list contains the critical tag.

    Both the tags and ``critical_tag`` are normalized by stripping a leading
    '@' prefix and whitespace before comparison.

    Args:
        tags: List of tag strings to search.
        critical_tag: The tag name that marks a scenario as critical.
            Defaults to ``"critical"``.

    Returns:
        True if the critical tag is present in the tag list.

    Raises:
        TypeError: If ``tags`` is not an iterable of strings.
    """
    _check_tags(tags)
    normalized = {_normalize_tag(t) for t in tags}
    return _normalize_tag(critical_tag) in normalized
