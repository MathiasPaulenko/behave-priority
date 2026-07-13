"""Exception hierarchy for behave-priority."""

from __future__ import annotations


class PriorityError(Exception):
    """Base exception for all behave-priority errors."""


class StopExecutionError(PriorityError):
    """Raised internally when fail-fast conditions are met.

    Attributes:
        reason: Human-readable description of why execution stopped.
        failed_count: Number of failures that triggered the stop.
        threshold: Failure threshold that was exceeded.
    """

    def __init__(self, reason: str, failed_count: int, threshold: int) -> None:
        """Initialize the exception.

        Args:
            reason: Human-readable description of why execution stopped.
            failed_count: Number of failures that triggered the stop.
            threshold: Failure threshold that was exceeded.
        """
        self.reason = reason
        self.failed_count = failed_count
        self.threshold = threshold
        super().__init__(f"{reason}: {failed_count}/{threshold} failures")


class PriorityParseError(PriorityError):
    """Raised when a priority tag has invalid syntax.

    For example, ``priority(abc)`` or ``priority(1.5)`` are invalid because
    the value inside the parentheses is not an integer.
    """
