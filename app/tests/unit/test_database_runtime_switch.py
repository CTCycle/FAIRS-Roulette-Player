# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import base64
import sqlite3
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from server.configurations.database_config import DatabaseConfigurationStore
from server.contracts.configuration import DatabaseSettings, JsonServerSettings
from server.contracts.database_configuration import DatabaseConfigurationInput
from server.repositories.application_settings import ApplicationSettingsRepository
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import initialize_database
from server.repositories.database.runtime import (
    DatabaseSwitchConflict,
    RuntimeDatabaseManager,
)
from server.services import database_configuration as database_configuration_module
from server.services.database_configuration import (
    DatabaseConfigurationService,
    DatabaseSwitchError,
)


###############################################################################
def _sqlite_settings() -> DatabaseSettings:
    return DatabaseSettings(True, None, None, None, None, None, None, False, None, 10, 1000)


###############################################################################
def _initialized_database(path: Path, polling_interval: float) -> FAIRSDatabase:
    settings = _sqlite_settings()
    initialize_database(settings, database_path=path)
    database = FAIRSDatabase(settings, database_path=path)
    repository = ApplicationSettingsRepository()
    saved = repository.ensure_row(database)
    repository.replace(
        database,
        JsonServerSettings.model_validate(
            {
                **saved.model_dump(mode="python"),
                "jobs": {"polling_interval": polling_interval},
            }
        ),
    )
    return database


###############################################################################
@pytest.fixture
def api_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(database_configuration_module, "run_startup_validations", lambda _settings: None)
    old_path = tmp_path / "old.db"
    old_database = _initialized_database(old_path, 2.0)
    runtime_database = RuntimeDatabaseManager(old_database)
    store = DatabaseConfigurationStore(
        tmp_path / "database-config.json",
        environment_file=tmp_path / ".env",
        password_protector=lambda value: base64.b64encode(value.encode()).decode(),
        password_unprotector=lambda value: base64.b64decode(value).decode(),
    )
    store.write(DatabaseConfigurationInput(backend="sqlite", sqlite_path=str(old_path)))

    application = SimpleNamespace(state=SimpleNamespace())
    application.state.lifecycle = "ready"
    application.state.recovery_message = None
    application.state.training_run_manager = SimpleNamespace(is_job_running=lambda: False)
    application.state.inference_service = SimpleNamespace(
        state=SimpleNamespace(has_sessions=lambda: False)
    )
    application.state.loaded_settings = ApplicationSettingsRepository().get(old_database)

    fail_candidate = {"enabled": False, "path": None}

    def activate_services(_loaded, app_settings):
        if fail_candidate["enabled"] and _loaded and _loaded.sqlite_path == fail_candidate["path"]:
            raise RuntimeError("injected service activation failure")
        application.state.loaded_settings = app_settings

    service = DatabaseConfigurationService(
        store=store,
        runtime_database=runtime_database,
        application=application,
        activate_services=activate_services,
    )
    application.state.database_configuration_service = service
    try:
        yield service, runtime_database, store, old_path, fail_candidate, application
    finally:
        runtime_database.dispose()


###############################################################################
def test_database_status_redacts_saved_password(api_runtime) -> None:
    service, runtime_database, store, _old_path, _fail, _application = api_runtime
    postgres = DatabaseConfigurationInput(
        backend="postgresql",
        host="db.example",
        database_name="fairs",
        username="service",
        password="never-return-this-secret",
    )
    store.write(postgres, password=postgres.password)

    response = service.get_status()

    assert response.configuration.password_configured is True
    assert "password" not in response.configuration.model_dump()
    assert "never-return-this-secret" not in response.model_dump_json()
    assert response.active_backend == "sqlite"
    assert runtime_database.active.settings.embedded_database is True


###############################################################################
def test_connection_test_does_not_activate_or_persist_candidate(api_runtime, tmp_path: Path) -> None:
    service, runtime_database, store, old_path, _fail, _application = api_runtime
    candidate_path = tmp_path / "test-only.db"
    candidate = DatabaseConfigurationInput(backend="sqlite", sqlite_path=str(candidate_path))

    response = service.test_connection(candidate)

    assert response.success is True
    assert response.message == "Connection to sqlite succeeded."
    assert candidate_path.exists()
    assert runtime_database.active.db_path == old_path
    assert store.current().sqlite_path == old_path


###############################################################################
def test_switch_loads_target_settings_without_copying_settings(
    api_runtime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runtime_database, store, old_path, _fail, application = api_runtime
    target_path = tmp_path / "target.db"
    target_database = _initialized_database(target_path, 3.5)
    target_database.dispose()
    candidate = DatabaseConfigurationInput(backend="sqlite", sqlite_path=str(target_path))
    initialize_target = database_configuration_module.initialize_database

    def initialize_after_drain(settings, *, database_path=None):
        assert runtime_database.is_switching
        initialize_target(settings, database_path=database_path)

    monkeypatch.setattr(
        database_configuration_module,
        "initialize_database",
        initialize_after_drain,
    )

    response = service.activate(candidate)

    assert response.status == "ready"
    assert response.active_backend == "sqlite"
    assert runtime_database.active.db_path == target_path
    assert store.current().sqlite_path == target_path
    assert ApplicationSettingsRepository().get(runtime_database).jobs.polling_interval == 3.5
    old_database = FAIRSDatabase(_sqlite_settings(), database_path=old_path)
    try:
        assert ApplicationSettingsRepository().get(old_database).jobs.polling_interval == 2.0
    finally:
        old_database.dispose()
    assert application.state.loaded_settings.jobs.polling_interval == 3.5


###############################################################################
def test_connection_and_unknown_schema_fail_without_changing_active_config(api_runtime, tmp_path: Path) -> None:
    service, runtime_database, store, old_path, _fail, _application = api_runtime
    directory_candidate = DatabaseConfigurationInput(
        backend="sqlite", sqlite_path=str(tmp_path / "directory.db")
    )
    (tmp_path / "directory.db").mkdir()
    failed_test = service.test_connection(directory_candidate)
    assert failed_test.success is False

    unknown_path = tmp_path / "unknown.db"
    with sqlite3.connect(unknown_path) as connection:
        connection.execute("CREATE TABLE unknown_schema (id INTEGER PRIMARY KEY)")
    with pytest.raises(DatabaseSwitchError, match="could not be initialized"):
        service.activate(
            DatabaseConfigurationInput(
                backend="sqlite", sqlite_path=str(unknown_path)
            )
        )
    assert runtime_database.active.db_path == old_path
    assert store.current().sqlite_path == old_path


###############################################################################
def test_activation_failure_rolls_back_to_previous_database(api_runtime, tmp_path: Path) -> None:
    service, runtime_database, store, old_path, fail_candidate, _application = api_runtime
    candidate_path = tmp_path / "activation-failure.db"
    _initialized_database(candidate_path, 4.0).dispose()
    fail_candidate.update({"enabled": True, "path": candidate_path})

    with pytest.raises(DatabaseSwitchError, match="previous database remains active"):
        service.activate(
            DatabaseConfigurationInput(
                backend="sqlite", sqlite_path=str(candidate_path)
            )
        )

    assert runtime_database.active.db_path == old_path
    assert store.current().sqlite_path == old_path


###############################################################################
def test_switch_conflicts_with_active_training_and_inference(api_runtime, tmp_path: Path) -> None:
    service, runtime_database, store, old_path, _fail, application = api_runtime
    target = DatabaseConfigurationInput(
        backend="sqlite", sqlite_path=str(tmp_path / "conflict.db")
    )
    application.state.training_run_manager.is_job_running = lambda: True

    with pytest.raises(DatabaseSwitchConflict, match="training"):
        service.activate(target)
    assert runtime_database.active.db_path == old_path
    assert store.current().sqlite_path == old_path

    application.state.training_run_manager.is_job_running = lambda: False
    application.state.inference_service.state.has_sessions = lambda: True
    with pytest.raises(DatabaseSwitchConflict, match="inference"):
        service.activate(target)


###############################################################################
def test_runtime_manager_drains_operations_before_switch(tmp_path: Path) -> None:
    database = _initialized_database(tmp_path / "drain.db", 1.0)
    manager = RuntimeDatabaseManager(database)
    operation_started = Event()
    allow_operation_to_finish = Event()
    switch_acquired = Event()

    def run_operation() -> None:
        with manager.operation():
            operation_started.set()
            allow_operation_to_finish.wait(timeout=2)

    def run_switch() -> None:
        with manager.switching(timeout_seconds=2):
            switch_acquired.set()

    operation_thread = Thread(target=run_operation)
    switch_thread = Thread(target=run_switch)
    try:
        operation_thread.start()
        assert operation_started.wait(timeout=1)
        switch_thread.start()
        assert not switch_acquired.wait(timeout=0.05)
        allow_operation_to_finish.set()
        assert switch_acquired.wait(timeout=1)
    finally:
        allow_operation_to_finish.set()
        operation_thread.join(timeout=1)
        switch_thread.join(timeout=1)
        manager.dispose()
