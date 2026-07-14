"""Unit tests for behave_priority.parallel."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from behave_priority.parallel import (
    ParallelCoordinator,
    cleanup_coordinator,
    create_coordinator,
    get_coord_dir,
)


class TestParallelCoordinator:
    """Tests for ParallelCoordinator file-based IPC."""

    def test_creates_worker_file(self, tmp_path: Path) -> None:
        ParallelCoordinator(tmp_path, worker_id="w1")
        assert (tmp_path / "worker_w1.json").exists()
        data = json.loads((tmp_path / "worker_w1.json").read_text())
        assert data["failed_count"] == 0
        assert data["critical_failed"] is False

    def test_report_failure_increments_count(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.report_failure()
        coord.report_failure()
        data = json.loads((tmp_path / "worker_w1.json").read_text())
        assert data["failed_count"] == 2
        assert data["critical_failed"] is False

    def test_report_critical_failure(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.report_failure(is_critical=True)
        data = json.loads((tmp_path / "worker_w1.json").read_text())
        assert data["failed_count"] == 1
        assert data["critical_failed"] is True

    def test_should_stop_local_failures(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.report_failure()
        coord.report_failure()
        coord.report_failure()
        assert coord.should_stop(stop_after_failures=3, stop_on_critical=False)

    def test_should_not_stop_below_threshold(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.report_failure()
        assert not coord.should_stop(stop_after_failures=3, stop_on_critical=False)

    def test_should_stop_on_critical(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.report_failure(is_critical=True)
        assert coord.should_stop(stop_after_failures=None, stop_on_critical=True)

    def test_should_not_stop_on_critical_when_disabled(
        self, tmp_path: Path
    ) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.report_failure(is_critical=True)
        assert not coord.should_stop(
            stop_after_failures=None, stop_on_critical=False
        )

    def test_aggregates_across_workers(self, tmp_path: Path) -> None:
        w1 = ParallelCoordinator(tmp_path, worker_id="w1")
        w2 = ParallelCoordinator(tmp_path, worker_id="w2")
        w1.report_failure()
        w1.report_failure()
        w2.report_failure()
        assert w1.should_stop(stop_after_failures=3, stop_on_critical=False)
        assert w2.should_stop(stop_after_failures=3, stop_on_critical=False)

    def test_aggregates_critical_across_workers(self, tmp_path: Path) -> None:
        w1 = ParallelCoordinator(tmp_path, worker_id="w1")
        w2 = ParallelCoordinator(tmp_path, worker_id="w2")
        w1.report_failure(is_critical=True)
        assert w2.should_stop(
            stop_after_failures=None, stop_on_critical=True
        )

    def test_cleanup_removes_worker_file(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert (tmp_path / "worker_w1.json").exists()
        coord.cleanup()
        assert not (tmp_path / "worker_w1.json").exists()

    def test_cleanup_idempotent(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.cleanup()
        coord.cleanup()

    def test_default_worker_id_is_pid(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path)
        assert coord.worker_id == str(os.getpid())
        coord.cleanup()

    def test_creates_coord_dir_if_not_exists(self, tmp_path: Path) -> None:
        coord_dir = tmp_path / "nested" / "coord"
        coord = ParallelCoordinator(coord_dir, worker_id="w1")
        assert coord_dir.exists()
        coord.cleanup()

    def test_ignores_corrupt_worker_files(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        (tmp_path / "worker_corrupt.json").write_text("not json")
        assert not coord.should_stop(
            stop_after_failures=1, stop_on_critical=False
        )
        coord.cleanup()

    def test_no_threshold_returns_false(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.report_failure()
        assert not coord.should_stop(
            stop_after_failures=None, stop_on_critical=False
        )
        coord.cleanup()


class TestCreateCoordinator:
    """Tests for create_coordinator factory function."""

    def test_returns_none_when_env_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("BEHAVE_PRIORITY_COORD_DIR", raising=False)
        assert create_coordinator() is None

    def test_returns_coordinator_when_env_set(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BEHAVE_PRIORITY_COORD_DIR", str(tmp_path))
        coord = create_coordinator(worker_id="test_w1")
        assert coord is not None
        assert coord.worker_id == "test_w1"
        coord.cleanup()

    def test_get_coord_dir_from_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("BEHAVE_PRIORITY_COORD_DIR", str(tmp_path))
        assert get_coord_dir() == str(tmp_path)


class TestCleanupCoordinator:
    """Tests for cleanup_coordinator context-based cleanup."""

    def test_cleanup_with_no_coordinator(self) -> None:
        class FakeCtx:
            pass

        cleanup_coordinator(FakeCtx())

    def test_cleanup_removes_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BEHAVE_PRIORITY_COORD_DIR", str(tmp_path))
        coord = create_coordinator(worker_id="test_w1")
        assert coord is not None

        class FakeCtx:
            pass

        ctx = FakeCtx()
        ctx._priority_coordinator = coord  # type: ignore[attr-defined]
        assert (tmp_path / "worker_test_w1.json").exists()
        cleanup_coordinator(ctx)
        assert not (tmp_path / "worker_test_w1.json").exists()

    def test_stale_file_overwritten_on_init(self, tmp_path: Path) -> None:
        stale = tmp_path / "worker_stale.json"
        stale.write_text(json.dumps({"failed_count": 5, "critical_failed": True}))
        coord = ParallelCoordinator(tmp_path, worker_id="stale")
        data = json.loads(stale.read_text())
        assert data["failed_count"] == 0
        assert data["critical_failed"] is False
        coord.cleanup()
