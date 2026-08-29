from __future__ import annotations

from pathlib import Path

import pytest

from server.contracts.configuration import (
    DatabaseSettings,
    DeviceSettings,
    JobsSettings,
    ServerSettings,
)
from server.services import startup_validation

###############################################################################
def _embedded_settings() -> ServerSettings:
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
def _external_settings(engine: str) -> ServerSettings:
    return ServerSettings(
        database=DatabaseSettings(
            embedded_database=False,
            engine=engine,
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
        jobs=JobsSettings(polling_interval=1.0),
        device=DeviceSettings(
            jit_compile=False,
            jit_backend="inductor",
            use_mixed_precision=False,
        ),
    )

###############################################################################
def test_startup_validations_create_runtime_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources_dir = tmp_path / "resources"
    logs_dir = resources_dir / "logs"
    checkpoints_dir = resources_dir / "checkpoints"

    monkeypatch.setattr(
        startup_validation.shared_paths, "RESOURCES_PATH", resources_dir
    )
    monkeypatch.setattr(startup_validation.shared_paths, "LOGS_PATH", logs_dir)
    monkeypatch.setattr(
        startup_validation.shared_paths,
        "CHECKPOINT_PATH",
        checkpoints_dir,
    )

    startup_validation.run_startup_validations(_embedded_settings())

    assert resources_dir.is_dir()
    assert logs_dir.is_dir()
    assert checkpoints_dir.is_dir()

###############################################################################
def test_external_database_validation_rejects_unsupported_engine() -> None:
    with pytest.raises(RuntimeError, match="Unsupported database engine"):
        startup_validation.run_startup_validations(_external_settings("mysql"))

###############################################################################
@pytest.mark.parametrize("engine", ["postgres", "postgresql", "postgresql+psycopg2"])
def test_external_database_validation_rejects_legacy_postgres_aliases(engine: str) -> None:
    with pytest.raises(RuntimeError, match="Unsupported database engine"):
        startup_validation.run_startup_validations(_external_settings(engine))
