from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil

import pandas as pd
import pytest
from sqlalchemy import create_engine, event, inspect, text

from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import (
    ALEMBIC_CONFIG_PATH,
    DatabaseMigrationError,
    run_migrations_on_engine,
)
from server.repositories.datasets import DatasetRepository
from server.repositories.inference import InferenceRepository
from server.repositories.schemas.models import Base

###############################################################################
def exercise_contract(database: FAIRSDatabase) -> None:
    run_migrations_on_engine(database.engine)
    datasets = DatasetRepository(database)
    inference = InferenceRepository(database)
    first = datasets.import_replacement("Example", "training", pd.DataFrame({"sequence_index": [0, 1], "outcome_id": [0, 32]}))
    second = datasets.import_replacement(" example ", "training", pd.DataFrame({"sequence_index": [0], "outcome_id": [19]}))
    assert first["dataset_id"] == second["dataset_id"]
    assert len(datasets.outcomes(first["dataset_id"])) == 1
    assert datasets.summaries("training")[0]["row_count"] == 1
    inference.upsert_session({"session_id": "contract-session", "dataset_id": first["dataset_id"], "checkpoint_name": "checkpoint", "initial_capital": 100})
    inference.upsert_step({"session_id": "contract-session", "step_number": 1, "bet_amount": 1, "predicted_action": 0, "capital_after": 99})
    datasets.delete(first["dataset_id"])
    with database.Session() as session:
        assert session.execute(text("SELECT COUNT(*) FROM inference_session_steps")).scalar_one() == 0

###############################################################################
def test_sqlite_contract() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    try:
        exercise_contract(FAIRSDatabase(engine=engine))
    finally:
        engine.dispose()

###############################################################################
def _reset_postgres(engine) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "DROP TABLE IF EXISTS inference_session_steps, inference_sessions, "
            "dataset_outcomes, datasets, alembic_version CASCADE"
        )

###############################################################################
@pytest.fixture
def postgres_engine():
    postgres_url = os.getenv("TEST_POSTGRES_URL")
    if not postgres_url:
        pytest.skip("PostgreSQL persistence coverage requires TEST_POSTGRES_URL")
    engine = create_engine(postgres_url, pool_pre_ping=True)
    _reset_postgres(engine)
    try:
        yield engine
    finally:
        _reset_postgres(engine)
        engine.dispose()

###############################################################################
def _copy_test_alembic_environment(tmp_path: Path, body: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source_root = ALEMBIC_CONFIG_PATH.parent
    fixture_root = tmp_path / "alembic-fixture"
    shutil.copytree(source_root / "alembic", fixture_root / "alembic")
    (fixture_root / "alembic.ini").write_text(
        ALEMBIC_CONFIG_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (fixture_root / "alembic" / "versions" / "0002_test_revision.py").write_text(
        body,
        encoding="utf-8",
    )
    return fixture_root / "alembic.ini"

###############################################################################
def _set_postgres_revision(engine, revision: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE alembic_version SET version_num = :revision"),
            {"revision": revision},
        )

###############################################################################
def test_postgresql_clean_and_current_are_idempotent(postgres_engine) -> None:
    run_migrations_on_engine(postgres_engine)
    run_migrations_on_engine(postgres_engine)
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial_schema"

###############################################################################
def test_postgresql_legacy_adoption_preserves_data(postgres_engine) -> None:
    # Deliberately construct the pre-Alembic legacy fixture.
    Base.metadata.create_all(postgres_engine)
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO datasets "
                "(dataset_name, dataset_name_key, dataset_kind, created_at, updated_at) "
                "VALUES ('Legacy', 'legacy', 'training', '2026-01-01', '2026-01-01')"
            )
        )

    run_migrations_on_engine(postgres_engine)

    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM datasets")).scalar_one() == 1
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial_schema"

###############################################################################
def test_postgresql_synthetic_rollback_and_behind_revision(
    postgres_engine,
    tmp_path: Path,
) -> None:
    run_migrations_on_engine(postgres_engine)
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
    with pytest.raises(DatabaseMigrationError, match="migration"):
        run_migrations_on_engine(postgres_engine, config_path=failure_config)
    with postgres_engine.connect() as connection:
        assert not inspect(connection).has_table("temporary_failure_table")
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial_schema"

    behind_config = _copy_test_alembic_environment(
        tmp_path / "behind",
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
    _set_postgres_revision(postgres_engine, "0001_initial_schema")
    run_migrations_on_engine(postgres_engine, config_path=behind_config)
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002_test_revision"

###############################################################################
def test_postgresql_concurrent_initializers_serialize(postgres_engine) -> None:
    def initialize() -> None:
        engine = create_engine(os.environ["TEST_POSTGRES_URL"], pool_pre_ping=True)
        try:
            run_migrations_on_engine(engine)
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(initialize) for _ in range(2)]
        for future in futures:
            future.result()

    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial_schema"

###############################################################################
def test_postgresql_contract(postgres_engine) -> None:
    exercise_contract(FAIRSDatabase(engine=postgres_engine))
