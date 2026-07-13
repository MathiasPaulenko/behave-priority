"""Unit tests for behave_priority.exceptions."""

from __future__ import annotations

import pytest

from behave_priority.exceptions import (
    PriorityError,
    PriorityParseError,
    StopExecutionError,
)


class TestPriorityError:
    def test_is_exception(self) -> None:
        assert issubclass(PriorityError, Exception)

    def test_can_be_raised(self) -> None:
        with pytest.raises(PriorityError, match="something went wrong"):
            raise PriorityError("something went wrong")

    def test_can_be_caught_as_exception(self) -> None:
        try:
            raise PriorityError("base error")
        except Exception:
            pass
        else:
            pytest.fail("PriorityError was not caught as Exception")


class TestStopExecutionError:
    def test_is_priority_error(self) -> None:
        assert issubclass(StopExecutionError, PriorityError)

    def test_is_exception(self) -> None:
        assert issubclass(StopExecutionError, Exception)

    def test_stores_reason(self) -> None:
        err = StopExecutionError("fail-fast triggered", failed_count=3, threshold=2)
        assert err.reason == "fail-fast triggered"

    def test_stores_failed_count(self) -> None:
        err = StopExecutionError("fail-fast triggered", failed_count=3, threshold=2)
        assert err.failed_count == 3

    def test_stores_threshold(self) -> None:
        err = StopExecutionError("fail-fast triggered", failed_count=3, threshold=2)
        assert err.threshold == 2

    def test_message_format(self) -> None:
        err = StopExecutionError("fail-fast triggered", failed_count=3, threshold=2)
        assert str(err) == "fail-fast triggered: 3/2 failures"

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(StopExecutionError) as exc_info:
            raise StopExecutionError("critical failure", failed_count=1, threshold=1)
        assert exc_info.value.reason == "critical failure"
        assert exc_info.value.failed_count == 1
        assert exc_info.value.threshold == 1

    def test_caught_as_priority_error(self) -> None:
        with pytest.raises(PriorityError):
            raise StopExecutionError("stop", failed_count=5, threshold=3)

    def test_zero_values(self) -> None:
        err = StopExecutionError("no failures", failed_count=0, threshold=0)
        assert err.failed_count == 0
        assert err.threshold == 0
        assert str(err) == "no failures: 0/0 failures"

    def test_negative_values(self) -> None:
        err = StopExecutionError("invalid", failed_count=-1, threshold=-1)
        assert err.failed_count == -1
        assert err.threshold == -1


class TestPriorityParseError:
    def test_is_priority_error(self) -> None:
        assert issubclass(PriorityParseError, PriorityError)

    def test_is_exception(self) -> None:
        assert issubclass(PriorityParseError, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(PriorityParseError, match="invalid tag"):
            raise PriorityParseError("invalid tag syntax")

    def test_caught_as_priority_error(self) -> None:
        with pytest.raises(PriorityError):
            raise PriorityParseError("bad tag")

    def test_caught_as_exception(self) -> None:
        try:
            raise PriorityParseError("bad tag")
        except Exception:
            pass
        else:
            pytest.fail("PriorityParseError was not caught as Exception")


class TestHierarchy:
    def test_all_inherit_from_priority_error(self) -> None:
        assert issubclass(StopExecutionError, PriorityError)
        assert issubclass(PriorityParseError, PriorityError)

    def test_stop_and_parse_are_distinct(self) -> None:
        assert not issubclass(StopExecutionError, PriorityParseError)
        assert not issubclass(PriorityParseError, StopExecutionError)

    def test_catch_all_with_priority_error(self) -> None:
        for exc in [
            PriorityError("base"),
            StopExecutionError("stop", failed_count=1, threshold=1),
            PriorityParseError("parse"),
        ]:
            try:
                raise exc
            except PriorityError:
                pass
            else:
                pytest.fail(f"Failed to catch {type(exc).__name__} as PriorityError")
