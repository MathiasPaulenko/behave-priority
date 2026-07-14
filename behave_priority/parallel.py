"""File-based coordination for parallel fail-fast across worker processes.

When behave runs with ``--parallel=N``, each worker is a separate process
with its own ``PriorityState``. This module provides a ``ParallelCoordinator``
that uses a shared directory with one JSON file per worker to track global
failure counts and critical failures.

Each worker writes its own file atomically (temp file + rename). To check
global state, all worker files in the coordination directory are read and
aggregated. This avoids the need for cross-process file locking.

Usage::

    # Before running behave with --parallel, set env var:
    #   BEHAVE_PRIORITY_COORD_DIR=/tmp/behave_priority_coord

    # In environment.py:
    setup_priority(context, stop_after_failures=3, parallel_coord=True)
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

_COORD_DIR_ENV = "BEHAVE_PRIORITY_COORD_DIR"


class ParallelCoordinator:
    """File-based coordination for parallel workers.

    Each worker creates and maintains its own JSON file in a shared
    coordination directory. The file contains the worker's failure
    count and critical-failure flag. Global state is computed by
    reading all worker files in the directory.

    Attributes:
        coord_dir: Directory where worker files are stored.
        worker_id: Unique identifier for this worker (defaults to PID).
    """

    def __init__(self, coord_dir: str | Path, worker_id: str | None = None) -> None:
        """Initialize the coordinator and create the worker file.

        If a stale file from a previous run exists (e.g. a worker that
        crashed without cleanup), it is overwritten with fresh state.

        Args:
            coord_dir: Path to the shared coordination directory.
                Will be created if it does not exist.
            worker_id: Unique identifier for this worker. If None,
                uses the process PID.
        """
        self.coord_dir = Path(coord_dir)
        self.coord_dir.mkdir(parents=True, exist_ok=True)
        self.worker_id = worker_id or str(os.getpid())
        self._worker_file = self.coord_dir / f"worker_{self.worker_id}.json"
        self._failed_count = 0
        self._critical_failed = False
        self._write_state()

    def report_failure(self, *, is_critical: bool = False) -> None:
        """Record a failure for this worker.

        Atomically updates the worker's file with the new failure count.

        Args:
            is_critical: Whether the failure was in a critical scenario.
        """
        self._failed_count += 1
        if is_critical:
            self._critical_failed = True
        self._write_state()

    def should_stop(
        self,
        stop_after_failures: int | None,
        stop_on_critical: bool,
    ) -> bool:
        """Check if global fail-fast conditions have been met.

        Reads all worker files in the coordination directory and
        aggregates failure counts and critical-failure flags.

        Args:
            stop_after_failures: Global failure threshold, or None.
            stop_on_critical: Whether to stop on any critical failure.

        Returns:
            True if global conditions indicate execution should stop.
        """
        global_failed = 0
        global_critical = False

        for f in self.coord_dir.glob("worker_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                global_failed += data.get("failed_count", 0)
                if data.get("critical_failed", False):
                    global_critical = True
            except (json.JSONDecodeError, OSError):
                continue

        if stop_after_failures is not None and global_failed >= stop_after_failures:
            return True
        return stop_on_critical and global_critical

    def cleanup(self) -> None:
        """Remove this worker's file from the coordination directory."""
        with contextlib.suppress(OSError):
            self._worker_file.unlink(missing_ok=True)

    def _write_state(self) -> None:
        """Atomically write this worker's state to its file."""
        data = {
            "failed_count": self._failed_count,
            "critical_failed": self._critical_failed,
        }
        tmp = self._worker_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(self._worker_file)


def get_coord_dir() -> str | None:
    """Get the coordination directory from the environment variable.

    Returns:
        The path from ``BEHAVE_PRIORITY_COORD_DIR`` env var, or None.
    """
    return os.environ.get(_COORD_DIR_ENV)


def create_coordinator(worker_id: str | None = None) -> ParallelCoordinator | None:
    """Create a ParallelCoordinator from the env var, if set.

    Args:
        worker_id: Optional worker identifier. Defaults to PID.

    Returns:
        A ``ParallelCoordinator`` if ``BEHAVE_PRIORITY_COORD_DIR`` is set,
        otherwise None.
    """
    coord_dir = get_coord_dir()
    if coord_dir is None:
        return None
    return ParallelCoordinator(coord_dir, worker_id=worker_id)


def cleanup_coordinator(context: object) -> None:
    """Clean up the parallel coordinator for this worker.

    Intended for use in ``after_all``. Removes the worker's file from
    the coordination directory.

    Args:
        context: Behave's context object.
    """
    coordinator: ParallelCoordinator | None = getattr(
        context, "_priority_coordinator", None
    )
    if coordinator is not None:
        coordinator.cleanup()
