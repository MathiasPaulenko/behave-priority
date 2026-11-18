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
import math
import os
import re
import time
import warnings
from pathlib import Path

_COORD_DIR_ENV = "BEHAVE_PRIORITY_COORD_DIR"

# Worker files created more than this many seconds before this coordinator
# started are considered stale (e.g. left behind by a crashed previous run)
# and are ignored when aggregating global state.
_CLOCK_SKEW_S = 120.0

# Worker IDs are interpolated into a filename inside the coordination
# directory. Restricting the charset prevents path traversal and special
# filenames from escaping or corrupting the directory.
_WORKER_ID_RE = re.compile(r"[A-Za-z0-9_.-]+")

# Retries for the final replace step of the atomic write. On Windows the
# rename can fail transiently when a peer process holds the destination
# file open for reading.
_REPLACE_RETRIES = 5
_REPLACE_DELAY_S = 0.01


def _read_worker_state(path: Path) -> tuple[float, int, bool] | None:
    """Read and validate a worker state file.

    Files are only produced by this library, but they may be truncated by
    a crashed writer or corrupted externally. Any malformed file is
    ignored rather than aborting the aggregation.

    Args:
        path: Path to a ``worker_*.json`` file.

    Returns:
        ``(created_at, failed_count, critical_failed)`` when the file is
        valid, otherwise None.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    # bool is an int subclass and must be rejected explicitly.
    # float() conversion may raise OverflowError on absurdly large ints.
    created_at = data.get("created_at")
    if isinstance(created_at, bool) or not isinstance(created_at, int | float):
        return None
    try:
        created_at = float(created_at)
    except OverflowError:
        return None
    if not math.isfinite(created_at):
        return None

    failed_count = data.get("failed_count")
    if isinstance(failed_count, bool) or not isinstance(failed_count, int | float):
        return None
    try:
        failed_count = float(failed_count)
    except OverflowError:
        return None
    if not math.isfinite(failed_count) or failed_count < 0:
        return None

    critical_failed = data.get("critical_failed")
    if not isinstance(critical_failed, bool):
        return None

    return created_at, int(failed_count), critical_failed


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
                uses the process PID. Only letters, digits, ``_``,
                ``-`` and ``.`` are allowed, since the value is
                interpolated into a filename.

        Raises:
            ValueError: If ``worker_id`` contains characters outside the
                allowed set, or ``coord_dir`` is empty.
            OSError: If the coordination directory cannot be created or
                written to.
        """
        if not str(coord_dir).strip():
            raise ValueError(f"coord_dir must not be empty, got {coord_dir!r}")
        self.worker_id = worker_id or str(os.getpid())
        if not isinstance(self.worker_id, str) or not _WORKER_ID_RE.fullmatch(self.worker_id):
            raise ValueError(
                f"worker_id must contain only letters, digits, '_', '-' "
                f"and '.', got {self.worker_id!r}"
            )
        self.coord_dir = Path(coord_dir)
        self.coord_dir.mkdir(parents=True, exist_ok=True)
        self._worker_file = self.coord_dir / f"worker_{self.worker_id}.json"
        self._failed_count = 0
        self._critical_failed = False
        self._write_warned = False
        self._started_at = time.time()
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
        try:
            self._write_state()
        except OSError:
            # A failing worker must not abort the test run; fail-fast
            # degrades to per-worker state until writes succeed again.
            if not self._write_warned:
                self._write_warned = True
                warnings.warn(
                    f"parallel coordinator: cannot write {self._worker_file}; "
                    "shared fail-fast state may be stale",
                    RuntimeWarning,
                    stacklevel=2,
                )

    def should_stop(
        self,
        stop_after_failures: int | None,
        stop_on_critical: bool,
    ) -> bool:
        """Check if global fail-fast conditions have been met.

        Reads all worker files in the coordination directory and
        aggregates failure counts and critical-failure flags. Files
        that fail to parse, or that were created before this run
        (stale files left by a crashed previous run), are ignored.

        Args:
            stop_after_failures: Global failure threshold, or None.
            stop_on_critical: Whether to stop on any critical failure.

        Returns:
            True if global conditions indicate execution should stop.
        """
        global_failed = 0
        global_critical = False
        min_created_at = self._started_at - _CLOCK_SKEW_S

        try:
            worker_files = self.coord_dir.glob("worker_*.json")
            for f in worker_files:
                state = _read_worker_state(f)
                if state is None:
                    continue
                created_at, failed_count, critical_failed = state
                if created_at < min_created_at:
                    continue
                global_failed += failed_count
                if critical_failed:
                    global_critical = True
        except OSError:
            # An unreadable coordination directory cannot abort the run;
            # with no readable state, global conditions are not met.
            pass

        if stop_after_failures is not None and global_failed >= stop_after_failures:
            return True
        return stop_on_critical and global_critical

    def cleanup(self) -> None:
        """Remove this worker's file from the coordination directory."""
        with contextlib.suppress(OSError):
            self._worker_file.unlink(missing_ok=True)
            self._worker_file.with_suffix(".tmp").unlink(missing_ok=True)

    def _write_state(self) -> None:
        """Atomically write this worker's state to its file."""
        data = {
            "failed_count": self._failed_count,
            "critical_failed": self._critical_failed,
            "created_at": self._started_at,
        }
        tmp = self._worker_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        for attempt in range(_REPLACE_RETRIES):
            try:
                tmp.replace(self._worker_file)
                return
            except OSError:
                if attempt == _REPLACE_RETRIES - 1:
                    raise
                time.sleep(_REPLACE_DELAY_S)


def get_coord_dir() -> str | None:
    """Get the coordination directory from the environment variable.

    Returns:
        The path from ``BEHAVE_PRIORITY_COORD_DIR`` env var, or None when
        the variable is unset, empty, or whitespace-only.
    """
    value = os.environ.get(_COORD_DIR_ENV)
    if value is None:
        return None
    value = value.strip()
    return value or None


def create_coordinator(worker_id: str | None = None) -> ParallelCoordinator | None:
    """Create a ParallelCoordinator from the env var, if set.

    Args:
        worker_id: Optional worker identifier. Defaults to PID.

    Returns:
        A ``ParallelCoordinator`` if ``BEHAVE_PRIORITY_COORD_DIR`` is set
        and usable, otherwise None. A warning is emitted when the
        directory exists in the env var but cannot be used.

    Raises:
        ValueError: If ``worker_id`` is invalid.
    """
    coord_dir = get_coord_dir()
    if coord_dir is None:
        return None
    try:
        return ParallelCoordinator(coord_dir, worker_id=worker_id)
    except OSError as e:
        warnings.warn(
            f"BEHAVE_PRIORITY_COORD_DIR={coord_dir!r} is not usable: {e}. "
            "Cross-process coordination is disabled.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None


def cleanup_coordinator(context: object) -> None:
    """Clean up the parallel coordinator for this worker.

    Intended for use in ``after_all``. Removes the worker's file from
    the coordination directory.

    Args:
        context: Behave's context object.
    """
    coordinator: ParallelCoordinator | None = getattr(context, "_priority_coordinator", None)
    if coordinator is not None:
        coordinator.cleanup()
