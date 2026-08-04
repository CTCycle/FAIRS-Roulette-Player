from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from server.domain.configuration import (
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
    connection_calls: list[bool] = []
    settings = settings or _build_settings()

    monkeypatch.setattr(app_module, "get_server_settings", lambda: settings)
    monkeypatch.setattr(
        app_module,
        "initialize_sqlite_database_if_missing",
        lambda database_settings: initialize_calls.append(database_settings),
    )
    monkeypatch.setattr(app_module, "run_startup_validations", lambda settings: None)

    class DatabaseStub:
        def check_connection(self) -> None:
            connection_calls.append(True)

    monkeypatch.setattr(app_module, "FAIRSDatabase", lambda *_args: DatabaseStub())
    monkeypatch.setattr(app_module, "DatasetRepository", lambda database: object())
    monkeypatch.setattr(app_module, "InferenceRepository", lambda database: object())
    monkeypatch.setattr(app_module, "DataSerializer", lambda **kwargs: object())
    monkeypatch.setattr(app_module, "create_job_manager", lambda: object())
    monkeypatch.setattr(app_module, "CheckpointService", lambda: object())
    monkeypatch.setattr(app_module, "DatasetImportService", lambda **kwargs: object())
    monkeypatch.setattr(app_module, "TabularFileLoader", lambda: object())
    monkeypatch.setattr(app_module, "DatasetService", lambda **kwargs: object())
    monkeypatch.setattr(app_module, "TrainingService", lambda **kwargs: object())
    monkeypatch.setattr(app_module, "InferenceService", lambda **kwargs: object())

    return initialize_calls, connection_calls

###############################################################################
def test_root_redirects_to_docs_when_client_build_is_missing(monkeypatch) -> None:
    import server.app as app_module

    initialize_calls, connection_calls = _stub_lifespan_dependencies(monkeypatch, app_module)
    monkeypatch.setenv("ENABLE_API_DOCS", "true")
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)

    application = app_module.create_app()

    with TestClient(application) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
    assert len(initialize_calls) == 1
    assert connection_calls == []

###############################################################################
def test_root_and_nested_routes_serve_built_client_when_available(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import server.app as app_module

    initialize_calls, connection_calls = _stub_lifespan_dependencies(monkeypatch, app_module)

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
    assert connection_calls == []

###############################################################################
def test_postgresql_startup_only_checks_existing_connection(monkeypatch) -> None:
    import server.app as app_module

    initialize_calls, connection_calls = _stub_lifespan_dependencies(
        monkeypatch,
        app_module,
        _build_external_settings(),
    )
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)

    application = app_module.create_app()

    with TestClient(application) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert initialize_calls == []
    assert connection_calls == [True]

###############################################################################
def test_postgresql_startup_reports_connection_failure(monkeypatch) -> None:
    import server.app as app_module

    _stub_lifespan_dependencies(monkeypatch, app_module, _build_external_settings())

    class FailingDatabase:
        def check_connection(self) -> None:
            raise SQLAlchemyError("connection refused")

    monkeypatch.setattr(app_module, "FAIRSDatabase", lambda *_args: FailingDatabase())
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)

    application = app_module.create_app()

    with pytest.raises(RuntimeError, match="Unable to connect to the configured PostgreSQL database"):
        with TestClient(application):
            pass
