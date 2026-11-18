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

    def test_should_not_stop_on_critical_when_disabled(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.report_failure(is_critical=True)
        assert not coord.should_stop(stop_after_failures=None, stop_on_critical=False)

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
        assert w2.should_stop(stop_after_failures=None, stop_on_critical=True)

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
        assert not coord.should_stop(stop_after_failures=1, stop_on_critical=False)
        coord.cleanup()

    def test_no_threshold_returns_false(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        coord.report_failure()
        assert not coord.should_stop(stop_after_failures=None, stop_on_critical=False)
        coord.cleanup()

    def test_ignores_stale_worker_files(self, tmp_path: Path) -> None:
        stale = tmp_path / "worker_old.json"
        stale.write_text(
            json.dumps(
                {
                    "failed_count": 10,
                    "critical_failed": True,
                    "created_at": 0.0,
                }
            )
        )
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert not coord.should_stop(stop_after_failures=1, stop_on_critical=True)
        coord.cleanup()

    def test_ignores_worker_files_without_created_at(self, tmp_path: Path) -> None:
        legacy = tmp_path / "worker_legacy.json"
        legacy.write_text(json.dumps({"failed_count": 10, "critical_failed": True}))
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert not coord.should_stop(stop_after_failures=1, stop_on_critical=True)
        coord.cleanup()


class TestCreateCoordinator:
    """Tests for create_coordinator factory function."""

    def test_returns_none_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
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

    def test_get_coord_dir_from_env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("BEHAVE_PRIORITY_COORD_DIR", str(tmp_path))
        assert get_coord_dir() == str(tmp_path)


class TestCleanupCoordinator:
    """Tests for cleanup_coordinator context-based cleanup."""

    def test_cleanup_with_no_coordinator(self) -> None:
        class FakeCtx:
            pass

        cleanup_coordinator(FakeCtx())

    def test_cleanup_removes_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


class TestWorkerFileValidation:
    """Regression tests: malformed-but-valid-JSON worker files must be
    ignored rather than crash or corrupt the aggregation."""

    def test_ignores_wrong_type_failed_count(self, tmp_path: Path) -> None:
        # Previously crashed with TypeError on 'int + str'.
        (tmp_path / "worker_bad.json").write_text(
            json.dumps({"failed_count": "x", "critical_failed": False, "created_at": 1.0})
        )
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False
        coord.cleanup()

    def test_ignores_bool_failed_count(self, tmp_path: Path) -> None:
        (tmp_path / "worker_bad.json").write_text(
            json.dumps({"failed_count": True, "critical_failed": False, "created_at": 1.0})
        )
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False
        coord.cleanup()

    def test_ignores_non_dict_json(self, tmp_path: Path) -> None:
        (tmp_path / "worker_bad.json").write_text("[1, 2, 3]")
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False
        coord.cleanup()

    def test_ignores_nan_created_at(self, tmp_path: Path) -> None:
        # NaN passes isinstance(float) but every comparison with it is
        # False, so it previously bypassed the stale-file filter.
        (tmp_path / "worker_bad.json").write_text(
            '{"failed_count": 5, "critical_failed": true, "created_at": NaN}'
        )
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False
        coord.cleanup()

    def test_ignores_infinite_created_at(self, tmp_path: Path) -> None:
        (tmp_path / "worker_bad.json").write_text(
            '{"failed_count": 5, "critical_failed": true, "created_at": Infinity}'
        )
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False
        coord.cleanup()

    def test_negative_failed_count_cannot_mask_failures(self, tmp_path: Path) -> None:
        # A negative failed_count would lower the global sum and mask
        # real failures from other workers.
        import time

        (tmp_path / "worker_bad.json").write_text(
            json.dumps(
                {
                    "failed_count": -10,
                    "critical_failed": False,
                    "created_at": time.time(),
                }
            )
        )
        other = ParallelCoordinator(tmp_path, worker_id="w2")
        other.report_failure()
        other.report_failure()
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert coord.should_stop(stop_after_failures=2, stop_on_critical=False) is True
        coord.cleanup()
        other.cleanup()

    def test_ignores_missing_required_fields(self, tmp_path: Path) -> None:
        (tmp_path / "worker_bad.json").write_text(json.dumps({"created_at": 1.0}))
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False
        coord.cleanup()

    def test_ignores_non_bool_critical_failed(self, tmp_path: Path) -> None:
        (tmp_path / "worker_bad.json").write_text(
            json.dumps({"failed_count": 0, "critical_failed": "yes", "created_at": 1.0})
        )
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False
        coord.cleanup()

    def test_ignores_huge_int_fields(self, tmp_path: Path) -> None:
        # Regression: math.isfinite() raises OverflowError on ints too
        # large to convert to float, which crashed should_stop().
        huge = "1" * 400
        (tmp_path / "worker_bad.json").write_text(
            '{"failed_count": 5, "critical_failed": true, "created_at": ' + huge + "}"
        )
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False

        (tmp_path / "worker_bad.json").write_text(
            '{"failed_count": ' + huge + ', "critical_failed": true, "created_at": 1.0}'
        )
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False
        coord.cleanup()


class TestWorkerIdValidation:
    """Regression tests: worker_id is interpolated into a filename and
    must not allow escaping the coordination directory."""

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="worker_id"):
            ParallelCoordinator(tmp_path, worker_id="a/../../evil")

    def test_rejects_forward_slash(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="worker_id"):
            ParallelCoordinator(tmp_path, worker_id="sub/dir")

    def test_rejects_backslash(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="worker_id"):
            ParallelCoordinator(tmp_path, worker_id="a\b")

    def test_rejects_null_byte(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="worker_id"):
            ParallelCoordinator(tmp_path, worker_id="a\x00b")

    def test_rejects_spaces_and_special_chars(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="worker_id"):
            ParallelCoordinator(tmp_path, worker_id="a b$c")

    def test_accepts_safe_characters(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="Worker-1.x_2")
        assert (tmp_path / "worker_Worker-1.x_2.json").exists()
        coord.cleanup()

    def test_empty_worker_id_defaults_to_pid(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="")
        assert coord.worker_id == str(os.getpid())
        coord.cleanup()

    def test_non_string_worker_id_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="worker_id"):
            ParallelCoordinator(tmp_path, worker_id=123)  # type: ignore[arg-type]


class TestCoordDirValidation:
    def test_empty_coord_dir_raises(self) -> None:
        # Path('') resolves to '.', which would silently write worker
        # files into the current working directory.
        with pytest.raises(ValueError, match="coord_dir"):
            ParallelCoordinator("")

    def test_whitespace_coord_dir_raises(self) -> None:
        with pytest.raises(ValueError, match="coord_dir"):
            ParallelCoordinator("   ")


class TestCoordDirHandling:
    """Regression tests for unusable coordination directories."""

    def test_create_coordinator_empty_env_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BEHAVE_PRIORITY_COORD_DIR", "")
        assert create_coordinator() is None
        assert get_coord_dir() is None

    def test_create_coordinator_whitespace_env_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BEHAVE_PRIORITY_COORD_DIR", "   ")
        assert create_coordinator() is None
        assert get_coord_dir() is None

    def test_get_coord_dir_strips_whitespace(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("BEHAVE_PRIORITY_COORD_DIR", f"  {tmp_path}  ")
        assert get_coord_dir() == str(tmp_path)

    def test_create_coordinator_dir_is_file_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        blocker = tmp_path / "notadir"
        blocker.write_text("x")
        monkeypatch.setenv("BEHAVE_PRIORITY_COORD_DIR", str(blocker))
        with pytest.warns(RuntimeWarning, match="not usable"):
            assert create_coordinator() is None


class TestWriteResilience:
    """Regression tests for write/read failure handling."""

    def test_report_failure_warns_instead_of_crashing(self, tmp_path: Path) -> None:
        import shutil

        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        shutil.rmtree(tmp_path)
        with pytest.warns(RuntimeWarning, match="cannot write"):
            coord.report_failure()
        # A second failure does not warn again.
        coord.report_failure()

    def test_should_stop_with_missing_dir_returns_false(self, tmp_path: Path) -> None:
        import shutil

        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        shutil.rmtree(tmp_path)
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False

    def test_should_stop_tolerates_glob_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")

        def bad_glob(self: Path, pattern: str) -> list[Path]:
            raise OSError("unreadable")

        monkeypatch.setattr(Path, "glob", bad_glob)
        assert coord.should_stop(stop_after_failures=1, stop_on_critical=True) is False

    def test_write_retries_transient_replace_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real_replace = Path.replace
        calls = {"n": 0}

        def flaky(self: Path, target: Path) -> Path:
            calls["n"] += 1
            if calls["n"] < 3:
                raise OSError("transient lock")
            return real_replace(self, target)

        monkeypatch.setattr(Path, "replace", flaky)
        ParallelCoordinator(tmp_path, worker_id="w1")
        assert (tmp_path / "worker_w1.json").exists()

    def test_write_state_raises_after_retry_exhaustion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def always_fail(self: Path, target: Path) -> Path:
            raise OSError("locked")

        monkeypatch.setattr(Path, "replace", always_fail)
        with pytest.raises(OSError, match="locked"):
            ParallelCoordinator(tmp_path, worker_id="w1")

    def test_cleanup_removes_leftover_tmp_file(self, tmp_path: Path) -> None:
        coord = ParallelCoordinator(tmp_path, worker_id="w1")
        (tmp_path / "worker_w1.tmp").write_text("junk")
        coord.cleanup()
        assert not (tmp_path / "worker_w1.json").exists()
        assert not (tmp_path / "worker_w1.tmp").exists()
