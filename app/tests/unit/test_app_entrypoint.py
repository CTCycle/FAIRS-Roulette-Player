from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from server.repositories.database.initializer import DatabaseInitializationError

from server.contracts.configuration import (
    DatabaseSettings,
    DeviceSettings,
    JobsSettings,
    ServerSettings,
)


###############################################################################
def _build_settings() -> ServerSettings:
    return ServerSettings(
        database=DatabaseSettings(
            embedded_database=True,
            engine=None,
            host=None,
            port=None,
            database_name=None,
            username=None,
            password=None,
            ssl=False,
            ssl_ca=None,
            connect_timeout=10,
            insert_batch_size=1000,
        ),
        jobs=JobsSettings(polling_interval=1.0),
        device=DeviceSettings(
            jit_compile=False,
            jit_backend="inductor",
            use_mixed_precision=False,
        ),
    )


###############################################################################
def _build_external_settings() -> ServerSettings:
    settings = _build_settings()
    return ServerSettings(
        database=DatabaseSettings(
            embedded_database=False,
            engine="postgresql+psycopg",
            host="db-host",
            port=5432,
            database_name="fairs",
            username="user",
            password="secret",
            ssl=False,
            ssl_ca=None,
            connect_timeout=10,
            insert_batch_size=1000,
        ),
        jobs=settings.jobs,
        device=settings.device,
    )


###############################################################################
def _stub_lifespan_dependencies(
    monkeypatch,
    app_module,
    settings: ServerSettings | None = None,
) -> tuple[list[object], list[bool]]:
    initialize_calls: list[object] = []
    dispose_calls: list[bool] = []
    settings = settings or _build_settings()

    monkeypatch.setattr(app_module, "get_server_settings", lambda: settings)
    monkeypatch.setattr(
        app_module,
        "initialize_database",
        lambda database_settings: initialize_calls.append(database_settings),
    )
    monkeypatch.setattr(app_module, "run_startup_validations", lambda settings: None)

    ###############################################################################
    class DatabaseStub:
        # -------------------------------------------------------------------------
        def dispose(self) -> None:
            dispose_calls.append(True)

    monkeypatch.setattr(app_module, "FAIRSDatabase", lambda *_args: DatabaseStub())
    monkeypatch.setattr(app_module, "DatasetRepository", lambda database: object())
    monkeypatch.setattr(app_module, "InferenceRepository", lambda database: object())
    monkeypatch.setattr(app_module, "TrainingRunManager", lambda: object())
    monkeypatch.setattr(app_module, "CheckpointService", lambda: object())
    monkeypatch.setattr(app_module, "DatasetImportService", lambda **kwargs: object())
    monkeypatch.setattr(app_module, "TabularFileLoader", lambda: object())
    monkeypatch.setattr(app_module, "DatasetService", lambda **kwargs: object())
    monkeypatch.setattr(app_module, "TrainingService", lambda **kwargs: object())
    monkeypatch.setattr(app_module, "InferenceService", lambda **kwargs: object())

    return initialize_calls, dispose_calls


###############################################################################
def test_root_redirects_to_docs_when_client_build_is_missing(monkeypatch) -> None:
    import server.app as app_module

    initialize_calls, dispose_calls = _stub_lifespan_dependencies(
        monkeypatch, app_module
    )
    monkeypatch.setenv("ENABLE_API_DOCS", "true")
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)

    application = app_module.create_app()

    with TestClient(application) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
    assert len(initialize_calls) == 1
    assert dispose_calls == [True]


###############################################################################
def test_root_returns_status_when_api_docs_are_disabled(monkeypatch) -> None:
    import server.app as app_module

    initialize_calls, dispose_calls = _stub_lifespan_dependencies(
        monkeypatch, app_module
    )
    monkeypatch.setenv("ENABLE_API_DOCS", "false")
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)

    application = app_module.create_app()

    with TestClient(application) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(initialize_calls) == 1
    assert dispose_calls == [True]


###############################################################################
def test_repeated_lifespan_entry_reinitializes_and_disposes_once_per_run(
    monkeypatch,
) -> None:
    import server.app as app_module

    initialize_calls, dispose_calls = _stub_lifespan_dependencies(
        monkeypatch, app_module
    )
    monkeypatch.setenv("ENABLE_API_DOCS", "false")
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)

    application = app_module.create_app()
    with TestClient(application) as first_client:
        assert first_client.get("/").json() == {"status": "ok"}
    with TestClient(application) as second_client:
        assert second_client.get("/").json() == {"status": "ok"}

    assert len(initialize_calls) == 2
    assert dispose_calls == [True, True]


###############################################################################
def test_root_and_nested_routes_serve_built_client_when_available(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import server.app as app_module

    initialize_calls, dispose_calls = _stub_lifespan_dependencies(
        monkeypatch, app_module
    )

    client_dist = tmp_path / "dist"
    assets_dir = client_dist / "assets"
    assets_dir.mkdir(parents=True)
    index_file = client_dist / "index.html"
    asset_file = assets_dir / "app.js"
    index_file.write_text("<html><body>FAIRS client</body></html>", encoding="utf-8")
    asset_file.write_text("console.log('fairs');", encoding="utf-8")

    monkeypatch.setattr(app_module.shared_paths, "CLIENT_DIST_PATH", client_dist)
    monkeypatch.setattr(app_module.shared_paths, "CLIENT_INDEX_FILE_PATH", index_file)
    monkeypatch.setattr(app_module.shared_paths, "CLIENT_ASSETS_PATH", assets_dir)
    monkeypatch.setattr(app_module, "_client_build_available", lambda: True)

    application = app_module.create_app()

    with TestClient(application) as client:
        root_response = client.get("/")
        nested_response = client.get("/training")
        asset_response = client.get("/assets/app.js")

    assert "FAIRS client" in root_response.text
    assert "FAIRS client" in nested_response.text
    assert "console.log('fairs');" in asset_response.text
    assert len(initialize_calls) == 1
    assert dispose_calls == [True]


###############################################################################
def test_postgresql_startup_runs_the_shared_initializer(monkeypatch) -> None:
    import server.app as app_module

    initialize_calls, dispose_calls = _stub_lifespan_dependencies(
        monkeypatch,
        app_module,
        _build_external_settings(),
    )
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)

    application = app_module.create_app()

    with TestClient(application) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert initialize_calls == [_build_external_settings().database]
    assert dispose_calls == [True]


###############################################################################
def test_postgresql_startup_reports_connection_failure(monkeypatch) -> None:
    import server.app as app_module

    _stub_lifespan_dependencies(monkeypatch, app_module, _build_external_settings())

    ###############################################################################
    monkeypatch.setattr(
        app_module,
        "initialize_database",
        lambda *_args: (_ for _ in ()).throw(
            DatabaseInitializationError("migration failed")
        ),
    )
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)

    application = app_module.create_app()

    with pytest.raises(DatabaseInitializationError, match="migration failed"):
        with TestClient(application):
            pass


###############################################################################
def test_app_factory_defers_runtime_bootstrap_until_lifespan(monkeypatch) -> None:
    import server.app as app_module

    bootstrap = Mock()
    monkeypatch.setattr(app_module, "bootstrap_runtime", bootstrap)

    app_module.create_app()

    bootstrap.assert_not_called()


###############################################################################
def test_lifespan_has_explicit_order_and_reverse_cleanup(monkeypatch) -> None:
    import server.app as app_module

    events: list[str] = []
    settings = _build_settings()
    monkeypatch.setattr(app_module, "bootstrap_runtime", lambda: events.append("bootstrap"))
    monkeypatch.setattr(app_module, "get_server_settings", lambda: (events.append("settings") or settings))
    monkeypatch.setattr(app_module, "ensure_single_process_runtime", lambda: events.append("workers"))
    monkeypatch.setattr(app_module, "get_application_version", lambda: "test")
    monkeypatch.setattr(app_module, "run_startup_validations", lambda _: events.append("validate"))
    monkeypatch.setattr(app_module, "initialize_database", lambda _: events.append("migrate"))
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)
    monkeypatch.setattr(app_module, "close_application_logging", lambda: events.append("logging"))

    class Database:
        def dispose(self) -> None:
            events.append("database")

    class TrainingManager:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        def shutdown(self) -> bool:
            events.append("training-manager")
            return True

    class Training:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        def shutdown(self) -> bool:
            events.append("training-service")
            return True

    class Inference:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        def shutdown(self) -> None:
            events.append("inference")

    monkeypatch.setattr(
        app_module,
        "FAIRSDatabase",
        lambda *_: (events.append("database-created") or Database()),
    )
    monkeypatch.setattr(app_module, "DatasetRepository", lambda *_: object())
    monkeypatch.setattr(app_module, "InferenceRepository", lambda *_: object())
    monkeypatch.setattr(app_module, "TrainingRunManager", TrainingManager)
    monkeypatch.setattr(app_module, "CheckpointService", lambda: object())
    monkeypatch.setattr(app_module, "DatasetImportService", lambda **_: object())
    monkeypatch.setattr(app_module, "TabularFileLoader", lambda: object())
    monkeypatch.setattr(app_module, "DatasetService", lambda **_: object())
    monkeypatch.setattr(app_module, "TrainingService", Training)
    monkeypatch.setattr(app_module, "InferenceService", Inference)

    application = app_module.create_app()
    with TestClient(application):
        assert application.state.lifecycle == "ready"

    assert application.state.lifecycle == "stopped"
    assert events[:6] == [
        "bootstrap",
        "settings",
        "workers",
        "validate",
        "migrate",
        "database-created",
    ]
    assert events[-5:] == [
        "inference",
        "training-service",
        "training-manager",
        "database",
        "logging",
    ]


###############################################################################
def test_lifespan_rolls_back_partial_initialization(monkeypatch) -> None:
    import server.app as app_module

    events: list[str] = []
    settings = _build_settings()
    monkeypatch.setattr(app_module, "bootstrap_runtime", lambda: None)
    monkeypatch.setattr(app_module, "get_server_settings", lambda: settings)
    monkeypatch.setattr(app_module, "run_startup_validations", lambda _: None)
    monkeypatch.setattr(app_module, "initialize_database", lambda _: None)
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)
    monkeypatch.setattr(app_module, "close_application_logging", lambda: events.append("logging"))

    class Database:
        def dispose(self) -> None:
            events.append("database")

    class TrainingManager:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        def shutdown(self) -> bool:
            events.append("training-manager")
            return True

    class Training:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        def shutdown(self) -> bool:
            events.append("training-service")
            return True

    monkeypatch.setattr(
        app_module,
        "FAIRSDatabase",
        lambda *_: (events.append("database-created") or Database()),
    )
    monkeypatch.setattr(app_module, "DatasetRepository", lambda *_: object())
    monkeypatch.setattr(app_module, "InferenceRepository", lambda *_: object())
    monkeypatch.setattr(app_module, "TrainingRunManager", TrainingManager)
    monkeypatch.setattr(app_module, "CheckpointService", lambda: object())
    monkeypatch.setattr(app_module, "DatasetImportService", lambda **_: object())
    monkeypatch.setattr(app_module, "TabularFileLoader", lambda: object())
    monkeypatch.setattr(app_module, "DatasetService", lambda **_: object())
    monkeypatch.setattr(app_module, "TrainingService", Training)
    monkeypatch.setattr(
        app_module,
        "InferenceService",
        lambda **_: (_ for _ in ()).throw(RuntimeError("inference init failed")),
    )

    application = app_module.create_app()
    with pytest.raises(RuntimeError, match="inference init failed"):
        with TestClient(application):
            pass

    assert application.state.lifecycle == "stopped"
    assert events == [
        "database-created",
        "training-service",
        "training-manager",
        "database",
        "logging",
    ]
