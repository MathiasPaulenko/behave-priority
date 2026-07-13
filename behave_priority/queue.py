"""Thread-safe priority queue for scenario execution."""

from __future__ import annotations

import heapq
import itertools
import threading
from typing import Generic, TypeVar

T = TypeVar("T")


class PriorityQueue(Generic[T]):
    """Thread-safe priority queue.

    Lower priority number = higher execution priority (runs first).
    FIFO order for equal priorities (stable).
    """

    def __init__(self, default_priority: int = 999) -> None:
        self._heap: list[tuple[int, int, T]] = []
        self._counter: itertools.count[int] = itertools.count()
        self._default_priority: int = default_priority
        self._lock: threading.Lock = threading.Lock()

    def add(self, item: T, priority: int | None = None) -> None:
        """Add an item to the queue."""
        prio = priority if priority is not None else self._default_priority
        with self._lock:
            heapq.heappush(self._heap, (prio, next(self._counter), item))

    def pop(self) -> T:
        """Remove and return the highest-priority item.

        Raises:
            IndexError: If the queue is empty.
        """
        with self._lock:
            if not self._heap:
                raise IndexError("pop from empty priority queue")
            return heapq.heappop(self._heap)[2]

    def peek(self) -> T:
        """Return the highest-priority item without removing it.

        Raises:
            IndexError: If the queue is empty.
        """
        with self._lock:
            if not self._heap:
                raise IndexError("peek from empty priority queue")
            return self._heap[0][2]

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)

    def __bool__(self) -> bool:
        with self._lock:
            return bool(self._heap)

    def __contains__(self, item: T) -> bool:
        with self._lock:
            return any(entry[2] == item for entry in self._heap)
