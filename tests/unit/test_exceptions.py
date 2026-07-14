"""Unit tests for behave_priority.exceptions."""

from __future__ import annotations

import pytest

from behave_priority.exceptions import (
    PriorityError,
    PriorityParseError,
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
        assert issubclass(PriorityParseError, PriorityError)

    def test_catch_all_with_priority_error(self) -> None:
        for exc in [
            PriorityError("base"),
            PriorityParseError("parse"),
        ]:
            try:
                raise exc
            except PriorityError:
                pass
            else:
                pytest.fail(f"Failed to catch {type(exc).__name__} as PriorityError")
