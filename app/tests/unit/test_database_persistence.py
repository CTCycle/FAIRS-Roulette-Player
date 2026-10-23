# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import shutil
import pytest
import base64
import sqlite3
from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from server.repositories.database.initializer import ALEMBIC_CONFIG_PATH, run_migrations_on_engine, validate_database_metadata, DatabaseMigrationError, DatabaseRevisionError, DatabaseSchemaDriftError, initialize_database
from concurrent.futures import ThreadPoolExecutor
from server.contracts.configuration import DatabaseSettings, JsonServerSettings
from server.repositories.database import initializer
from server.repositories.schemas.models import Base
from threading import Event, Thread
from types import SimpleNamespace
from server.configurations.database_config import DatabaseConfigurationStore
from server.contracts.database_configuration import DatabaseConfigurationInput
from server.repositories.application_settings import ApplicationSettingsRepository
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.runtime import DatabaseSwitchConflict, RuntimeDatabaseManager
from server.services import database_configuration as database_configuration_module
from server.services.database_configuration import DatabaseConfigurationService, DatabaseSwitchError

###############################################################################
def test_alembic_history_has_one_current_schema_baseline() -> None:
    config = Config(str(ALEMBIC_CONFIG_PATH))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["0001_current_schema"]
    assert script.get_revision("0001_current_schema").down_revision is None

###############################################################################
def test_alembic_check_and_model_metadata_match_head(tmp_path: Path) -> None:
    database_path = tmp_path / "consistency.db"
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        run_migrations_on_engine(engine)
        with engine.connect() as connection:
            validate_database_metadata(connection)
            config = Config(str(ALEMBIC_CONFIG_PATH))
            config.attributes["connection"] = connection
            command.check(config)
    finally:
        engine.dispose()

###############################################################################
def _sqlite_settings() -> DatabaseSettings:
    return DatabaseSettings(
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
    )

###############################################################################
def _engine(database_path: Path):
    return create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )

###############################################################################
def _table_names(database_path: Path) -> set[str]:
    engine = _engine(database_path)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

###############################################################################
def _copy_test_alembic_environment(
    tmp_path: Path,
    revision_body: str,
) -> Path:
    source_root = initializer.ALEMBIC_CONFIG_PATH.parent
    fixture_root = tmp_path / "alembic-fixture"
    shutil.copytree(source_root / "alembic", fixture_root / "alembic")
    (fixture_root / "alembic.ini").write_text(
        initializer.ALEMBIC_CONFIG_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (fixture_root / "alembic" / "versions" / "0002_test_revision.py").write_text(
        revision_body,
        encoding="utf-8",
    )
    return fixture_root / "alembic.ini"

###############################################################################
def _set_revision(database_path: Path, revision: str) -> None:
    engine = _engine(database_path)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE alembic_version SET version_num = :revision"),
                {"revision": revision},
            )
    finally:
        engine.dispose()

###############################################################################
def test_clean_sqlite_initialization_creates_exact_alembic_schema(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "database.db"

    initialize_database(_sqlite_settings(), database_path=database_path)

    assert _table_names(database_path) == {
        "alembic_version",
        "datasets",
        "dataset_outcomes",
        "inference_sessions",
        "inference_session_steps",
        "application_settings",
    }
    engine = _engine(database_path)
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == "0001_current_schema"
            )
            initializer.validate_database_metadata(connection)
    finally:
        engine.dispose()

###############################################################################
def test_at_head_rerun_is_idempotent_and_preserves_rows(tmp_path: Path) -> None:
    database_path = tmp_path / "database.db"
    settings = _sqlite_settings()
    initialize_database(settings, database_path=database_path)

    engine = _engine(database_path)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO datasets "
                    "(dataset_name, dataset_name_key, dataset_kind, created_at, updated_at) "
                    "VALUES ('Example', 'example', 'training', '2026-01-01', '2026-01-01')"
                )
            )
    finally:
        engine.dispose()

    initialize_database(settings, database_path=database_path)

    engine = _engine(database_path)
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT COUNT(*) FROM datasets")).scalar_one()
                == 1
            )
    finally:
        engine.dispose()

###############################################################################
def test_populated_unversioned_database_is_rejected_without_mutation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy.db"
    legacy_engine = _engine(database_path)
    try:
        # Deliberately construct the pre-Alembic legacy fixture.
        Base.metadata.create_all(legacy_engine)
        with legacy_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO datasets "
                    "(dataset_name, dataset_name_key, dataset_kind, created_at, updated_at) "
                    "VALUES ('Legacy', 'legacy', 'training', '2026-01-01', '2026-01-01')"
                )
            )
    finally:
        legacy_engine.dispose()

    with pytest.raises(
        DatabaseRevisionError, match="non-empty database has no Alembic revision"
    ):
        initialize_database(_sqlite_settings(), database_path=database_path)

    engine = _engine(database_path)
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT COUNT(*) FROM datasets")).scalar_one()
                == 1
            )
            assert "alembic_version" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()

###############################################################################
def test_partial_unversioned_schema_is_rejected_unchanged(tmp_path: Path) -> None:
    database_path = tmp_path / "partial.db"
    legacy_engine = _engine(database_path)
    try:
        # Deliberately construct an incomplete unversioned fixture.
        Base.metadata.tables["datasets"].create(legacy_engine)
    finally:
        legacy_engine.dispose()

    with pytest.raises(
        DatabaseRevisionError, match="non-empty database has no Alembic revision"
    ):
        initialize_database(_sqlite_settings(), database_path=database_path)

    assert _table_names(database_path) == {"datasets"}

###############################################################################
def test_unknown_or_ahead_revision_is_rejected_before_schema_changes(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "ahead.db"
    engine = _engine(database_path)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('9999_ahead')")
            )
    finally:
        engine.dispose()

    with pytest.raises(DatabaseRevisionError, match="unknown|ahead"):
        initialize_database(_sqlite_settings(), database_path=database_path)

    assert _table_names(database_path) == {"alembic_version"}

###############################################################################
def test_previous_database_head_is_rejected_without_mutation(tmp_path: Path) -> None:
    database_path = tmp_path / "previous-head.db"
    engine = _engine(database_path)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
            connection.execute(
                text(
                    "INSERT INTO alembic_version (version_num) "
                    "VALUES ('0003_application_settings')"
                )
            )
    finally:
        engine.dispose()

    with pytest.raises(DatabaseRevisionError, match="unknown|ahead"):
        initialize_database(_sqlite_settings(), database_path=database_path)

    assert _table_names(database_path) == {"alembic_version"}

###############################################################################
def test_multiple_database_heads_are_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "multiple-heads.db"
    engine = _engine(database_path)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
            connection.execute(
                text(
                    "INSERT INTO alembic_version (version_num) VALUES ('0001_current_schema')"
                )
            )
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('9999_other')")
            )
    finally:
        engine.dispose()

    with pytest.raises(DatabaseRevisionError, match="multiple Alembic heads"):
        initialize_database(_sqlite_settings(), database_path=database_path)

###############################################################################
def test_metadata_drift_at_head_is_rejected_without_repair(tmp_path: Path) -> None:
    database_path = tmp_path / "drift.db"
    settings = _sqlite_settings()
    initialize_database(settings, database_path=database_path)
    engine = _engine(database_path)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE datasets ADD COLUMN unexpected TEXT"
            )
    finally:
        engine.dispose()

    with pytest.raises(DatabaseSchemaDriftError, match="drift|exactly match"):
        initialize_database(settings, database_path=database_path)

    engine = _engine(database_path)
    try:
        assert "unexpected" in {
            column["name"] for column in inspect(engine).get_columns("datasets")
        }
    finally:
        engine.dispose()

###############################################################################
def test_failed_migration_rolls_back_schema_and_revision(tmp_path: Path) -> None:
    database_path = tmp_path / "rollback.db"
    settings = _sqlite_settings()
    initialize_database(settings, database_path=database_path)
    failure_config = _copy_test_alembic_environment(
        tmp_path,
        '''"""Test-only failing revision."""
from alembic import op

revision = "0002_test_revision"
down_revision = "0001_current_schema"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("temporary_failure_table")
    raise RuntimeError("synthetic migration failure")

def downgrade() -> None:
    pass
''',
    )
    _set_revision(database_path, "0001_current_schema")

    engine = _engine(database_path)
    try:
        with pytest.raises(DatabaseMigrationError, match="migration"):
            run_migrations_on_engine(engine, config_path=failure_config)
        assert "temporary_failure_table" not in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == "0001_current_schema"
            )
    finally:
        engine.dispose()

###############################################################################
def test_known_behind_revision_upgrades_in_order(tmp_path: Path) -> None:
    database_path = tmp_path / "behind.db"
    settings = _sqlite_settings()
    initialize_database(settings, database_path=database_path)
    behind_config = _copy_test_alembic_environment(
        tmp_path,
        '''"""Test-only no-op revision."""
revision = "0002_test_revision"
down_revision = "0001_current_schema"
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
''',
    )
    _set_revision(database_path, "0001_current_schema")

    engine = _engine(database_path)
    try:
        run_migrations_on_engine(engine, config_path=behind_config)
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == "0002_test_revision"
            )
    finally:
        engine.dispose()

###############################################################################
def test_concurrent_sqlite_initializers_serialize_and_finish_at_head(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "concurrent.db"
    settings = _sqlite_settings()

    def initialize() -> None:
        initialize_database(settings, database_path=database_path)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(initialize) for _ in range(2)]
        for future in futures:
            future.result()

    engine = _engine(database_path)
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == "0001_current_schema"
            )
    finally:
        engine.dispose()

# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

###############################################################################
def _runtime_sqlite_settings() -> DatabaseSettings:
    return DatabaseSettings(True, None, None, None, None, None, None, False, None, 10, 1000)

###############################################################################
def _initialized_database(path: Path, polling_interval: float) -> FAIRSDatabase:
    settings = _runtime_sqlite_settings()
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
    old_database = FAIRSDatabase(_runtime_sqlite_settings(), database_path=old_path)
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
