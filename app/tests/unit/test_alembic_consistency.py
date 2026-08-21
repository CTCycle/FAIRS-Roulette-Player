from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from server.repositories.database.initializer import (
    ALEMBIC_CONFIG_PATH,
    run_migrations_on_engine,
    validate_database_metadata,
)

###############################################################################
def test_alembic_history_has_one_immutable_baseline_head() -> None:
    config = Config(str(ALEMBIC_CONFIG_PATH))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["0001_initial_schema"]
    assert script.get_revision("0001_initial_schema").down_revision is None

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
