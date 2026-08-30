from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2].parent
APP_ROOT = REPOSITORY_ROOT / "app"
CLIENT_SOURCE_ROOT = APP_ROOT / "client" / "src"
SERVER_ROOT = APP_ROOT / "server"

###############################################################################
def _source_text(root: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in root.rglob("*")
        if path.is_file() and "node_modules" not in path.parts
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
    ):
        assert forbidden not in client_source

    app_source = (SERVER_ROOT / "app.py").read_text(encoding="utf-8")
    assert "DataStore" not in app_source
    assert "JobManager" not in app_source

###############################################################################
def test_frontend_package_does_not_duplicate_backend_version_authority() -> None:
    package = json.loads(
        (CLIENT_SOURCE_ROOT.parent / "package.json").read_text(encoding="utf-8")
    )

    assert "version" not in package
