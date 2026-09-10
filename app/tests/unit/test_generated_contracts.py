from __future__ import annotations

from pathlib import Path

from scripts.generate_frontend_contracts import OUTPUT_PATH, render_typescript


###############################################################################
def test_generated_frontend_contract_matches_runtime_backend_contract() -> None:
    expected_path = (
        Path(__file__).resolve().parents[2]
        / "client"
        / "src"
        / "generated"
        / "api.ts"
    )
    assert OUTPUT_PATH == expected_path
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render_typescript()
