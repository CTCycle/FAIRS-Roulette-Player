from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil

import pytest
from sqlalchemy import create_engine, inspect, text

from server.contracts.configuration import DatabaseSettings
from server.repositories.database import initializer
from server.repositories.database.initializer import (
    DatabaseMigrationError,
    DatabaseRevisionError,
    DatabaseSchemaDriftError,
    initialize_database,
    run_migrations_on_engine,
)
from server.repositories.schemas.models import Base

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
            connection.execute(text("UPDATE alembic_version SET version_num = :revision"), {"revision": revision})
    finally:
        engine.dispose()

###############################################################################
def test_clean_sqlite_initialization_creates_exact_alembic_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "database.db"

    initialize_database(_sqlite_settings(), database_path=database_path)

    assert _table_names(database_path) == {
        "alembic_version",
        "datasets",
        "dataset_outcomes",
        "inference_sessions",
        "inference_session_steps",
    }
    engine = _engine(database_path)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial_schema"
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
            assert connection.execute(text("SELECT COUNT(*) FROM datasets")).scalar_one() == 1
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

    with pytest.raises(DatabaseRevisionError, match="non-empty database has no Alembic revision"):
        initialize_database(_sqlite_settings(), database_path=database_path)

    engine = _engine(database_path)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM datasets")).scalar_one() == 1
            assert "alembic_version" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()

###############################################################################
def test_partial_legacy_schema_is_rejected_unchanged(tmp_path: Path) -> None:
    database_path = tmp_path / "partial.db"
    legacy_engine = _engine(database_path)
    try:
        # Deliberately construct an incomplete pre-Alembic legacy fixture.
        Base.metadata.tables["datasets"].create(legacy_engine)
    finally:
        legacy_engine.dispose()

    with pytest.raises(DatabaseRevisionError, match="non-empty database has no Alembic revision"):
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
def test_multiple_database_heads_are_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "multiple-heads.db"
    engine = _engine(database_path)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema')")
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
            connection.exec_driver_sql("ALTER TABLE datasets ADD COLUMN unexpected TEXT")
    finally:
        engine.dispose()

    with pytest.raises(DatabaseSchemaDriftError, match="drift|exactly match"):
        initialize_database(settings, database_path=database_path)

    engine = _engine(database_path)
    try:
        assert "unexpected" in {
            column["name"]
            for column in inspect(engine).get_columns("datasets")
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
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("temporary_failure_table")
    raise RuntimeError("synthetic migration failure")

def downgrade() -> None:
    pass
''',
    )
    _set_revision(database_path, "0001_initial_schema")

    engine = _engine(database_path)
    try:
        with pytest.raises(DatabaseMigrationError, match="migration"):
            run_migrations_on_engine(engine, config_path=failure_config)
        assert "temporary_failure_table" not in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial_schema"
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
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
''',
    )
    _set_revision(database_path, "0001_initial_schema")

    engine = _engine(database_path)
    try:
        run_migrations_on_engine(engine, config_path=behind_config)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002_test_revision"
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
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial_schema"
    finally:
        engine.dispose()
