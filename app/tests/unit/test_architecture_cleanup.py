from __future__ import annotations

import json
from pathlib import Path

from scripts.export_openapi import render_openapi


REPOSITORY_ROOT = Path(__file__).resolve().parents[2].parent
APP_ROOT = REPOSITORY_ROOT / "app"
CLIENT_SOURCE_ROOT = APP_ROOT / "client" / "src"
SERVER_ROOT = APP_ROOT / "server"
TEXT_SOURCE_SUFFIXES = {
    ".bat",
    ".ini",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

###############################################################################
def _source_text(root: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in TEXT_SOURCE_SUFFIXES
        and "node_modules" not in path.parts
    )

###############################################################################
def test_legacy_state_and_persistence_paths_are_removed() -> None:
    obsolete_paths = (
        SERVER_ROOT / "repositories" / "serialization",
        SERVER_ROOT / "repositories" / "queries",
        SERVER_ROOT / "services" / "jobs.py",
        CLIENT_SOURCE_ROOT / "context" / "AppStateContext.tsx",
        CLIENT_SOURCE_ROOT / "context" / "AppStateStore.ts",
        CLIENT_SOURCE_ROOT / "hooks" / "useAppState.ts",
        APP_ROOT / "shared" / "openapi.json",
    )
    assert all(not path.exists() for path in obsolete_paths)

    client_source = _source_text(CLIENT_SOURCE_ROOT)
    for forbidden in (
        "AppStateProvider",
        "useAppState",
        "dataset_source",
        "datasetSource",
        "sessionState",
        "gameConfig",
        "uploadedDatasetName",
        "predicted_confidence",
    ):
        assert forbidden not in client_source

    runtime_source = _source_text(SERVER_ROOT)
    for forbidden in (
        "normalize_strategy_id",
        "fallback_strategy_id",
        "get_poll_interval_seconds",
    ):
        assert forbidden not in runtime_source

    launcher_source = (REPOSITORY_ROOT / "start_on_windows.ps1").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "knownLegacyCachePaths",
        "Get-DiscoveredLegacyCachePaths",
        "Get-LegacyCachePaths",
        ".angular",
        "Recreating a virtual environment that may reference an older repository location",
        "$defaults = [ordered]@{",
    ):
        assert forbidden not in launcher_source

    app_source = (SERVER_ROOT / "app.py").read_text(encoding="utf-8")
    assert "DataStore" not in app_source
    assert "JobManager" not in app_source

    openapi = json.loads(render_openapi())
    assert set(
        openapi["components"]["schemas"]["InferenceStartRequest"]["properties"]
    ) == {
        "checkpoint",
        "dataset_id",
        "game_capital",
        "game_bet",
    }
    assert set(openapi["components"]["schemas"]["HealthResponse"]["properties"]) == {
        "status",
        "application",
        "version",
    }
    prediction_properties = openapi["components"]["schemas"]["PredictionResponse"][
        "properties"
    ]
    assert "relative_preference" in prediction_properties
    assert "confidence" not in prediction_properties

    checkpoint_summary = openapi["components"]["schemas"][
        "TrainingCheckpointSummary"
    ]["properties"]
    assert "qnet_neurons" in checkpoint_summary
    assert "neurons" not in checkpoint_summary

###############################################################################
def test_frontend_package_does_not_duplicate_backend_version_authority() -> None:
    package = json.loads(
        (CLIENT_SOURCE_ROOT.parent / "package.json").read_text(encoding="utf-8")
    )

    assert "version" not in package
