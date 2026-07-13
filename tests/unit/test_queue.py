"""Unit tests for behave_priority.queue."""

from __future__ import annotations

import threading

import pytest

from behave_priority.queue import PriorityQueue


class TestAddAndPop:
    def test_single_item(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        assert q.pop() == "a"

    def test_lower_priority_pops_first(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("low", priority=10)
        q.add("high", priority=1)
        assert q.pop() == "high"
        assert q.pop() == "low"

    def test_three_items_ordered(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("c", priority=3)
        q.add("a", priority=1)
        q.add("b", priority=2)
        assert q.pop() == "a"
        assert q.pop() == "b"
        assert q.pop() == "c"

    def test_negative_priority(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("normal", priority=5)
        q.add("urgent", priority=-10)
        assert q.pop() == "urgent"

    def test_zero_priority(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("zero", priority=0)
        q.add("one", priority=1)
        assert q.pop() == "zero"

    def test_pop_empty_raises(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        with pytest.raises(IndexError, match="pop from empty"):
            q.pop()

    def test_pop_after_all_removed_raises(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        q.pop()
        with pytest.raises(IndexError, match="pop from empty"):
            q.pop()


class TestPeek:
    def test_peek_returns_highest_priority(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("low", priority=10)
        q.add("high", priority=1)
        assert q.peek() == "high"

    def test_peek_does_not_remove(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        assert q.peek() == "a"
        assert len(q) == 1
        assert q.pop() == "a"

    def test_peek_empty_raises(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        with pytest.raises(IndexError, match="peek from empty"):
            q.peek()

    def test_peek_after_pop_raises(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        q.pop()
        with pytest.raises(IndexError, match="peek from empty"):
            q.peek()


class TestFIFO:
    def test_equal_priorities_fifo(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("first", priority=1)
        q.add("second", priority=1)
        q.add("third", priority=1)
        assert q.pop() == "first"
        assert q.pop() == "second"
        assert q.pop() == "third"

    def test_equal_priorities_with_mixed(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a1", priority=1)
        q.add("b1", priority=1)
        q.add("a0", priority=0)
        q.add("c1", priority=1)
        assert q.pop() == "a0"
        assert q.pop() == "a1"
        assert q.pop() == "b1"
        assert q.pop() == "c1"

    def test_large_fifo_batch(self) -> None:
        q: PriorityQueue[int] = PriorityQueue()
        for i in range(100):
            q.add(i, priority=5)
        for i in range(100):
            assert q.pop() == i


class TestDefaultPriority:
    def test_default_priority_used_when_none(self) -> None:
        q: PriorityQueue[str] = PriorityQueue(default_priority=100)
        q.add("no_prio")
        q.add("explicit", priority=50)
        assert q.pop() == "explicit"
        assert q.pop() == "no_prio"

    def test_custom_default_priority(self) -> None:
        q: PriorityQueue[str] = PriorityQueue(default_priority=0)
        q.add("default")
        q.add("lower", priority=10)
        assert q.pop() == "default"

    def test_default_priority_999(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("default")
        q.add("high", priority=1)
        assert q.pop() == "high"
        assert q.pop() == "default"


class TestLen:
    def test_empty_len_zero(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        assert len(q) == 0

    def test_len_after_add(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        assert len(q) == 1

    def test_len_after_multiple_adds(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        q.add("b", priority=2)
        q.add("c", priority=3)
        assert len(q) == 3

    def test_len_after_pop(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        q.add("b", priority=2)
        q.pop()
        assert len(q) == 1

    def test_len_after_all_popped(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        q.pop()
        assert len(q) == 0


class TestBool:
    def test_empty_is_false(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        assert bool(q) is False

    def test_non_empty_is_true(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        assert bool(q) is True

    def test_false_after_all_popped(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        q.pop()
        assert bool(q) is False

    def test_if_empty(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        if q:
            pytest.fail("Empty queue should be falsy")
        q.add("a", priority=1)
        if not q:
            pytest.fail("Non-empty queue should be truthy")


class TestContains:
    def test_present(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        assert "a" in q

    def test_absent(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        assert "b" not in q

    def test_empty_queue(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        assert "a" not in q

    def test_after_pop(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        q.pop()
        assert "a" not in q

    def test_multiple_items(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        q.add("b", priority=2)
        q.add("c", priority=3)
        assert "a" in q
        assert "b" in q
        assert "c" in q
        assert "d" not in q


class TestThreadSafety:
    def test_concurrent_add_pop(self) -> None:
        q: PriorityQueue[int] = PriorityQueue()
        results: list[int] = []
        results_lock = threading.Lock()
        errors: list[Exception] = []
        stop = threading.Event()

        def producer() -> None:
            try:
                for i in range(200):
                    q.add(i, priority=i)
            except Exception as e:
                errors.append(e)

        def consumer() -> None:
            try:
                while not stop.is_set() or len(q) > 0:
                    try:
                        item = q.pop()
                        with results_lock:
                            results.append(item)
                    except IndexError:
                        break
            except Exception as e:
                errors.append(e)

        producers = [threading.Thread(target=producer) for _ in range(3)]
        consumers = [threading.Thread(target=consumer) for _ in range(3)]

        for p in producers:
            p.start()
        for p in producers:
            p.join()

        stop.set()
        for c in consumers:
            c.start()
        for c in consumers:
            c.join()

        assert errors == []
        expected = list(range(200)) * 3
        assert sorted(results) == sorted(expected)

    def test_concurrent_add_only(self) -> None:
        q: PriorityQueue[int] = PriorityQueue()
        threads: list[threading.Thread] = []

        def add_items(start: int) -> None:
            for i in range(start, start + 100):
                q.add(i, priority=i)

        for s in range(0, 500, 100):
            t = threading.Thread(target=add_items, args=(s,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(q) == 500
        prev = -1
        while q:
            item = q.pop()
            assert item > prev
            prev = item


class TestGenericType:
    def test_int_type(self) -> None:
        q: PriorityQueue[int] = PriorityQueue()
        q.add(42, priority=1)
        q.add(10, priority=2)
        assert q.pop() == 42

    def test_string_type(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("hello", priority=1)
        assert q.pop() == "hello"

    def test_custom_object_type(self) -> None:
        q: PriorityQueue[tuple[str, int]] = PriorityQueue()
        q.add(("a", 1), priority=2)
        q.add(("b", 2), priority=1)
        assert q.pop() == ("b", 2)


class TestEdgeCases:
    def test_add_same_item_twice(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        q.add("a", priority=2)
        assert len(q) == 2
        assert q.pop() == "a"
        assert q.pop() == "a"

    def test_peek_consistent(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=1)
        assert q.peek() == "a"
        assert q.peek() == "a"
        assert len(q) == 1

    def test_interleaved_add_pop(self) -> None:
        q: PriorityQueue[str] = PriorityQueue()
        q.add("a", priority=3)
        q.add("b", priority=1)
        assert q.pop() == "b"
        q.add("c", priority=0)
        assert q.pop() == "c"
        assert q.pop() == "a"
        assert len(q) == 0
