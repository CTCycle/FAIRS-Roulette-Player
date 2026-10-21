# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

from pathlib import Path
import time
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
from server.repositories.database.initializer import DatabaseInitializationError

from server.contracts.configuration import (
    DatabaseSettings,
    DeviceSettings,
    JobsSettings,
    JsonServerSettings,
    ServerSettings,
)
from server.configurations.database_config import LoadedDatabaseConfiguration

###############################################################################
class CheckpointServiceStub:

    def cleanup_incomplete_workspaces(self) -> None:
        return None


###############################################################################
class InferenceServiceStub:

    def shutdown(self) -> None:
        return None


###############################################################################
class TrainingRunManagerStub:

    def shutdown(self) -> bool:
        return True

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

    loaded_database = LoadedDatabaseConfiguration(
        document=None,
        settings=settings.database,
        sqlite_path=Path("configured-test.db") if settings.database.embedded_database else None,
    )

    ###############################################################################
    class StoreStub:

        # -------------------------------------------------------------------------
        def load_or_initialize(self):
            return loaded_database

        # -------------------------------------------------------------------------
        def current(self):
            return loaded_database

    monkeypatch.setattr(app_module, "DatabaseConfigurationStore", StoreStub)
    monkeypatch.setattr(
        app_module,
        "ApplicationSettingsRepository",
        lambda: SimpleNamespace(ensure_row=lambda *_args, **_kwargs: JsonServerSettings()),
    )
    monkeypatch.setattr(
        app_module,
        "initialize_database",
        lambda database_settings, **_kwargs: initialize_calls.append(database_settings),
    )
    monkeypatch.setattr(app_module, "run_startup_validations", lambda settings: None)

    ###############################################################################
    class DatabaseStub:

        # -------------------------------------------------------------------------
        def dispose(self) -> None:
            dispose_calls.append(True)

    monkeypatch.setattr(
        app_module,
        "FAIRSDatabase",
        lambda *_args, **_kwargs: DatabaseStub(),
    )
    monkeypatch.setattr(app_module, "DatasetRepository", lambda database: object())
    monkeypatch.setattr(app_module, "InferenceRepository", lambda database: object())
    monkeypatch.setattr(app_module, "TrainingRunManager", TrainingRunManagerStub)
    monkeypatch.setattr(app_module, "CheckpointService", CheckpointServiceStub)
    monkeypatch.setattr(app_module, "DatasetImportService", lambda **kwargs: object())
    monkeypatch.setattr(app_module, "TabularFileLoader", lambda: object())
    monkeypatch.setattr(app_module, "DatasetService", lambda **kwargs: object())

    ###############################################################################
    class TrainingServiceStub:

        # -------------------------------------------------------------------------
        def get_runtime_settings(self):
            return settings.jobs, settings.device

        # -------------------------------------------------------------------------
        def apply_runtime_settings(self, *_args):
            return None

        # -------------------------------------------------------------------------
        def apply_roulette_settings(self, *_args):
            return None

        # -------------------------------------------------------------------------
        def apply_database_settings(self, *_args):
            return None

        # -------------------------------------------------------------------------
        def shutdown(self) -> bool:
            return True

    monkeypatch.setattr(app_module, "TrainingService", lambda **_kwargs: TrainingServiceStub())
    monkeypatch.setattr(app_module, "InferenceService", lambda **kwargs: InferenceServiceStub())

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
def test_cors_allowlist_is_read_from_runtime_environment(monkeypatch) -> None:
    from fastapi import FastAPI
    from server.app import RuntimeCORSMiddleware

    monkeypatch.setenv(
        "CORS_ORIGINS",
        " https://console.example.test,https://admin.example.test ",
    )
    application = FastAPI()
    application.add_api_route("/health", lambda: {"status": "ok"}, methods=["GET"])
    application.add_middleware(RuntimeCORSMiddleware)

    with TestClient(application) as client:
        allowed = client.options(
            "/health",
            headers={
                "Origin": "https://console.example.test",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = client.options(
            "/health",
            headers={
                "Origin": "https://unlisted.example.test",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://console.example.test"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers

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

    ###############################################################################
    class ShutdownSpy:

        # -------------------------------------------------------------------------
        def __init__(self) -> None:
            self.shutdown_calls = 0

        # -------------------------------------------------------------------------
        def shutdown(self) -> None:
            self.shutdown_calls += 1

        # -------------------------------------------------------------------------
        def apply_runtime_settings(self, *_args) -> None:
            return None

        # -------------------------------------------------------------------------
        def apply_roulette_settings(self, *_args) -> None:
            return None

        # -------------------------------------------------------------------------
        def apply_database_settings(self, *_args) -> None:
            return None

    ###############################################################################
    class DatabaseSpy:

        # -------------------------------------------------------------------------
        def __init__(self) -> None:
            self.dispose_calls = 0

        # -------------------------------------------------------------------------
        def dispose(self) -> None:
            self.dispose_calls += 1
            dispose_calls.append(True)

    managers: list[ShutdownSpy] = []
    training_services: list[ShutdownSpy] = []
    inference_services: list[ShutdownSpy] = []
    databases: list[DatabaseSpy] = []

    def build_spy(values: list[ShutdownSpy]) -> ShutdownSpy:
        spy = ShutdownSpy()
        values.append(spy)
        return spy

    monkeypatch.setattr(
        app_module,
        "FAIRSDatabase",
        lambda *_args, **_kwargs: (databases.append(DatabaseSpy()) or databases[-1]),
    )
    monkeypatch.setattr(
        app_module,
        "TrainingRunManager",
        lambda: build_spy(managers),
    )
    monkeypatch.setattr(
        app_module,
        "TrainingService",
        lambda **_kwargs: build_spy(training_services),
    )
    monkeypatch.setattr(
        app_module,
        "InferenceService",
        lambda **_kwargs: build_spy(inference_services),
    )

    application = app_module.create_app()
    cycle_durations: list[float] = []
    for _cycle in range(4):
        started_at = time.perf_counter()
        with TestClient(application) as client:
            assert application.state.lifecycle == "ready"
            assert client.get("/").json() == {"status": "ok"}
        assert application.state.lifecycle == "stopped"
        cycle_durations.append(time.perf_counter() - started_at)

    assert len(initialize_calls) == 4
    assert len(databases) == 4
    assert [database.dispose_calls for database in databases] == [1, 1, 1, 1]
    assert dispose_calls == [True, True, True, True]
    assert len(managers) == len(training_services) == len(inference_services) == 4
    assert [manager.shutdown_calls for manager in managers] == [1, 1, 1, 1]
    assert [service.shutdown_calls for service in training_services] == [1] * 4
    assert [service.shutdown_calls for service in inference_services] == [1] * 4
    print(
        "VAL22 application lifecycles: "
        f"cycles={len(cycle_durations)}, total={sum(cycle_durations):.4f}s, "
        f"per_cycle={[round(value, 4) for value in cycle_durations]}, "
        f"max={max(cycle_durations):.4f}s, timeout=none (unit TestClient path)"
    )

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
        health_response = client.get("/api/health")
        unknown_api_response = client.get("/api/no-such-route")

    assert "FAIRS client" in root_response.text
    assert "FAIRS client" in nested_response.text
    assert "console.log('fairs');" in asset_response.text
    assert health_response.status_code == 200
    assert health_response.json()["application"] == "FAIRS"
    assert health_response.json()["status"] == "ok"
    assert unknown_api_response.status_code == 404
    assert unknown_api_response.json()["detail"] == "API route not found"
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
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            DatabaseInitializationError("migration failed")
        ),
    )
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)

    application = app_module.create_app()

    with TestClient(application) as client:
        assert application.state.lifecycle == "recovery"
        health = client.get("/api/health")

    assert health.status_code == 200
    assert health.json()["status"] == "recovery"

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
    _stub_lifespan_dependencies(monkeypatch, app_module, settings)
    monkeypatch.setattr(app_module, "bootstrap_runtime", lambda: events.append("bootstrap"))
    monkeypatch.setattr(app_module, "ensure_single_process_runtime", lambda: events.append("workers"))
    monkeypatch.setattr(app_module, "get_application_version", lambda: "test")
    monkeypatch.setattr(app_module, "run_startup_validations", lambda _: events.append("validate"))
    monkeypatch.setattr(app_module, "initialize_database", lambda *_args, **_kwargs: events.append("migrate"))
    loaded_database = LoadedDatabaseConfiguration(
        document=None,
        settings=settings.database,
        sqlite_path=Path("configured-test.db"),
    )
    monkeypatch.setattr(
        app_module,
        "DatabaseConfigurationStore",
        lambda: SimpleNamespace(
            load_or_initialize=lambda: (events.append("settings") or loaded_database),
            current=lambda: loaded_database,
        ),
    )
    monkeypatch.setattr(
        app_module,
        "ApplicationSettingsRepository",
        lambda: SimpleNamespace(
            ensure_row=lambda *_args, **_kwargs: JsonServerSettings()
        ),
    )
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)
    monkeypatch.setattr(app_module, "close_application_logging", lambda: events.append("logging"))

    ###############################################################################
    class Database:

        # -------------------------------------------------------------------------
        def dispose(self) -> None:
            events.append("database")

    ###############################################################################
    class TrainingManager:

        # -------------------------------------------------------------------------
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        # -------------------------------------------------------------------------
        def shutdown(self) -> bool:
            events.append("training-manager")
            return True

    ###############################################################################
    class Training:

        # -------------------------------------------------------------------------
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        # -------------------------------------------------------------------------
        def shutdown(self) -> bool:
            events.append("training-service")
            return True

        # -------------------------------------------------------------------------
        def apply_runtime_settings(self, *_args) -> None:
            return None

        # -------------------------------------------------------------------------
        def apply_roulette_settings(self, *_args) -> None:
            return None

        # -------------------------------------------------------------------------
        def apply_database_settings(self, *_args) -> None:
            return None

    ###############################################################################
    class Inference:

        # -------------------------------------------------------------------------
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        # -------------------------------------------------------------------------
        def shutdown(self) -> None:
            events.append("inference")

    monkeypatch.setattr(
        app_module,
        "FAIRSDatabase",
        lambda *_args, **_kwargs: (events.append("database-created") or Database()),
    )
    monkeypatch.setattr(app_module, "DatasetRepository", lambda *_: object())
    monkeypatch.setattr(app_module, "InferenceRepository", lambda *_: object())
    monkeypatch.setattr(app_module, "TrainingRunManager", TrainingManager)
    monkeypatch.setattr(app_module, "CheckpointService", CheckpointServiceStub)
    monkeypatch.setattr(app_module, "DatasetImportService", lambda **_: object())
    monkeypatch.setattr(app_module, "TabularFileLoader", lambda: object())
    monkeypatch.setattr(app_module, "DatasetService", lambda **_: object())
    monkeypatch.setattr(app_module, "TrainingService", Training)
    monkeypatch.setattr(app_module, "InferenceService", Inference)

    application = app_module.create_app()
    with TestClient(application):
        assert application.state.lifecycle == "ready"

    assert application.state.lifecycle == "stopped"
    assert events[:7] == [
        "bootstrap",
        "workers",
        "settings",
        "validate",
        "migrate",
        "database-created",
        "validate",
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
    _stub_lifespan_dependencies(monkeypatch, app_module, settings)
    monkeypatch.setattr(app_module, "bootstrap_runtime", lambda: None)
    monkeypatch.setattr(app_module, "run_startup_validations", lambda _: None)
    monkeypatch.setattr(app_module, "initialize_database", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_module, "_client_build_available", lambda: False)
    monkeypatch.setattr(app_module, "close_application_logging", lambda: events.append("logging"))

    ###############################################################################
    class Database:

        # -------------------------------------------------------------------------
        def dispose(self) -> None:
            events.append("database")

    ###############################################################################
    class TrainingManager:

        # -------------------------------------------------------------------------
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        # -------------------------------------------------------------------------
        def shutdown(self) -> bool:
            events.append("training-manager")
            return True

    ###############################################################################
    class Training:

        # -------------------------------------------------------------------------
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        # -------------------------------------------------------------------------
        def shutdown(self) -> bool:
            events.append("training-service")
            return True

        # -------------------------------------------------------------------------
        def apply_runtime_settings(self, *_args) -> None:
            return None

        # -------------------------------------------------------------------------
        def apply_roulette_settings(self, *_args) -> None:
            return None

        # -------------------------------------------------------------------------
        def apply_database_settings(self, *_args) -> None:
            return None

    monkeypatch.setattr(
        app_module,
        "FAIRSDatabase",
        lambda *_args, **_kwargs: (events.append("database-created") or Database()),
    )
    monkeypatch.setattr(app_module, "DatasetRepository", lambda *_: object())
    monkeypatch.setattr(app_module, "InferenceRepository", lambda *_: object())
    monkeypatch.setattr(app_module, "TrainingRunManager", TrainingManager)
    monkeypatch.setattr(app_module, "CheckpointService", CheckpointServiceStub)
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
    with TestClient(application):
        assert application.state.lifecycle == "recovery"

    assert application.state.lifecycle == "stopped"
    assert events.count("database-created") == 1
    assert events.count("database") == 1
    assert events.count("training-service") == 1
    assert events.count("training-manager") == 1
    assert events.count("logging") == 1
