from __future__ import annotations

from pathlib import Path

from scripts.export_openapi import OPENAPI_PATH, render_openapi


def test_shared_openapi_snapshot_matches_runtime_contract() -> None:
    assert OPENAPI_PATH == Path(__file__).resolve().parents[2] / "shared" / "openapi.json"
    assert OPENAPI_PATH.read_text(encoding="utf-8") == render_openapi()
