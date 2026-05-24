"""Tests for driftwatch.drift_summary_exporter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.runner import RunSummary
from driftwatch.drift_summary_exporter import (
    ExportedSummary,
    build_export,
    write_export,
)


def _target(name: str = "cfg") -> WatchTarget:
    return WatchTarget(
        name=name,
        local_path=Path(f"/etc/{name}.toml"),
        remote_url=f"https://example.com/{name}.toml",
    )


def _ok_result() -> DriftResult:
    return DriftResult.ok()


def _drift_result() -> DriftResult:
    r = DriftResult.__new__(DriftResult)
    object.__setattr__(r, "status", "drift")
    object.__setattr__(r, "message", "checksums differ")
    return r


def _error_result() -> DriftResult:
    r = DriftResult.__new__(DriftResult)
    object.__setattr__(r, "status", "error")
    object.__setattr__(r, "message", "file not found")
    return r


def _summary(pairs) -> RunSummary:
    has_drift = any(r.status in ("drift", "error") for _, r in pairs)
    return RunSummary(results=pairs, has_drift=has_drift)


# ---------------------------------------------------------------------------
# build_export
# ---------------------------------------------------------------------------

class TestBuildExport:
    def test_clean_summary_counts(self):
        s = _summary([(_target("a"), _ok_result()), (_target("b"), _ok_result())])
        exp = build_export(s, now=1_000.0)
        assert exp.clean == 2
        assert exp.drifted == 0
        assert exp.errors == 0
        assert exp.has_drift is False
        assert exp.total_targets == 2

    def test_mixed_summary_counts(self):
        s = _summary([
            (_target("a"), _ok_result()),
            (_target("b"), _drift_result()),
            (_target("c"), _error_result()),
        ])
        exp = build_export(s, now=1_000.0)
        assert exp.clean == 1
        assert exp.drifted == 1
        assert exp.errors == 1
        assert exp.has_drift is True

    def test_exported_at_uses_provided_timestamp(self):
        s = _summary([(_target(), _ok_result())])
        exp = build_export(s, now=42.5)
        assert exp.exported_at == 42.5

    def test_target_fields_present(self):
        t = _target("myapp")
        s = _summary([(t, _ok_result())])
        exp = build_export(s, now=0.0)
        assert len(exp.targets) == 1
        entry = exp.targets[0]
        assert entry["name"] == "myapp"
        assert entry["status"] == "ok"
        assert "remote_url" in entry
        assert "local_path" in entry

    def test_as_json_is_valid_json(self):
        s = _summary([(_target(), _drift_result())])
        exp = build_export(s, now=0.0)
        parsed = json.loads(exp.as_json())
        assert parsed["has_drift"] is True


# ---------------------------------------------------------------------------
# write_export
# ---------------------------------------------------------------------------

class TestWriteExport:
    def test_writes_file(self, tmp_path):
        out = tmp_path / "export" / "summary.json"
        s = _summary([(_target(), _ok_result())])
        write_export(s, out, now=1.0)
        assert out.exists()

    def test_written_content_is_valid_json(self, tmp_path):
        out = tmp_path / "summary.json"
        s = _summary([(_target(), _drift_result())])
        write_export(s, out, now=1.0)
        data = json.loads(out.read_text())
        assert data["has_drift"] is True
        assert data["drifted"] == 1

    def test_returns_exported_summary(self, tmp_path):
        out = tmp_path / "summary.json"
        s = _summary([(_target(), _ok_result())])
        result = write_export(s, out, now=5.0)
        assert isinstance(result, ExportedSummary)
        assert result.exported_at == 5.0

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "a" / "b" / "c" / "summary.json"
        s = _summary([(_target(), _ok_result())])
        write_export(s, out, now=0.0)
        assert out.exists()
