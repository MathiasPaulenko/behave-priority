"""Exception hierarchy for behave-priority."""

from __future__ import annotations


class PriorityError(Exception):
    """Base exception for all behave-priority errors."""


class StopExecutionError(PriorityError):
    """Raised internally when fail-fast conditions are met."""

    def __init__(self, reason: str, failed_count: int, threshold: int) -> None:
        self.reason = reason
        self.failed_count = failed_count
        self.threshold = threshold
        super().__init__(f"{reason}: {failed_count}/{threshold} failures")


class PriorityParseError(PriorityError):
    """Raised when a priority tag has invalid syntax."""
