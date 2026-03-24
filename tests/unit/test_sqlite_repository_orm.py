from __future__ import annotations

from datetime import datetime

import pandas as pd

from FAIRS.server.domain.configuration import DatabaseSettings
from FAIRS.server.repositories.database import sqlite as sqlite_module
from FAIRS.server.repositories.database.initializer import seed_roulette_outcomes
from FAIRS.server.repositories.database.sqlite import SQLiteRepository


# -----------------------------------------------------------------------------
def build_sqlite_settings(insert_batch_size: int = 2) -> DatabaseSettings:
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
        insert_batch_size=insert_batch_size,
    )


# -----------------------------------------------------------------------------
def build_datasets_frame(*rows: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


# -----------------------------------------------------------------------------
def test_sqlite_repository_orm_load_filter_delete(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sqlite_module, "RESOURCES_PATH", str(tmp_path))
    monkeypatch.setattr(sqlite_module, "DATABASE_FILENAME", "orm_test.db")

    repository = SQLiteRepository(build_sqlite_settings(), initialize_schema=True)
    rows = build_datasets_frame(
        {
            "dataset_id": "1",
            "dataset_name": "alpha",
            "dataset_kind": "training",
            "created_at": datetime(2026, 1, 1),
        },
        {
            "dataset_id": "2",
            "dataset_name": "beta",
            "dataset_kind": "inference",
            "created_at": datetime(2026, 1, 2),
        },
    )

    repository.append_into_database(rows, "datasets")
    all_rows = repository.load_from_database("datasets")
    training_rows = repository.load_filtered("datasets", {"dataset_kind": "training"})

    assert len(all_rows) == 2
    assert len(training_rows) == 1
    assert str(training_rows.iloc[0]["dataset_name"]) == "alpha"

    repository.delete_from_database("datasets", {"dataset_id": "1"})
    remaining = repository.load_from_database("datasets")
    assert len(remaining) == 1
    assert str(remaining.iloc[0]["dataset_id"]) == "2"


# -----------------------------------------------------------------------------
def test_sqlite_repository_orm_upsert_uses_unique_constraints(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(sqlite_module, "RESOURCES_PATH", str(tmp_path))
    monkeypatch.setattr(sqlite_module, "DATABASE_FILENAME", "orm_upsert.db")

    repository = SQLiteRepository(build_sqlite_settings(insert_batch_size=1), initialize_schema=True)

    first = build_datasets_frame(
        {
            "dataset_id": "1",
            "dataset_name": "roulette",
            "dataset_kind": "training",
            "created_at": datetime(2026, 1, 1),
        }
    )
    second = build_datasets_frame(
        {
            "dataset_id": "99",
            "dataset_name": "roulette",
            "dataset_kind": "training",
            "created_at": datetime(2026, 1, 3),
        }
    )

    repository.upsert_into_database(first, "datasets")
    repository.upsert_into_database(second, "datasets")

    loaded = repository.load_filtered(
        "datasets",
        {"dataset_kind": "training", "dataset_name": "roulette"},
    )
    assert len(loaded) == 1
    assert str(loaded.iloc[0]["dataset_id"]) == "99"


# -----------------------------------------------------------------------------
def test_seed_roulette_outcomes_is_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sqlite_module, "RESOURCES_PATH", str(tmp_path))
    monkeypatch.setattr(sqlite_module, "DATABASE_FILENAME", "seed.db")

    repository = SQLiteRepository(build_sqlite_settings(), initialize_schema=True)

    seed_roulette_outcomes(repository.engine)
    seed_roulette_outcomes(repository.engine)

    loaded = repository.load_from_database("roulette_outcomes")
    assert len(loaded) == 37
