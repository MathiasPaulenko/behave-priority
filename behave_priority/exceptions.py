"""Exception hierarchy for behave-priority."""

from __future__ import annotations


class PriorityError(Exception):
    """Base exception for all behave-priority errors."""


class PriorityParseError(PriorityError):
    """Raised when a priority tag has invalid syntax.

    For example, ``priority(abc)`` or ``priority(1.5)`` are invalid because
    the value inside the parentheses is not an integer.
    """
