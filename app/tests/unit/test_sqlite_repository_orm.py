from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, event, text

from server.domain.configuration import DatabaseSettings
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.datasets import DatasetRepository
from server.repositories.inference import InferenceRepository


def build_sqlite_settings(insert_batch_size: int = 2) -> DatabaseSettings:
    return DatabaseSettings(True, None, None, None, None, None, None, False, None, 10, insert_batch_size)


def test_sqlite_persistence_contract() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    database = FAIRSDatabase(build_sqlite_settings(), engine=engine)
    database.create_schema()
    datasets = DatasetRepository(database)
    inference = InferenceRepository(database)

    first = datasets.import_replacement(" Roulette ", "training", pd.DataFrame({"sequence_index": [0, 1, 2], "outcome_id": [0, 32, 15]}))
    second = datasets.import_replacement("roulette", "training", pd.DataFrame({"sequence_index": [0], "outcome_id": [19]}))
    assert first["dataset_id"] == second["dataset_id"]
    assert len(datasets.outcomes(first["dataset_id"])) == 1
    assert datasets.summaries("training")[0]["row_count"] == 1

    inference.upsert_session({"session_id": "session_1", "dataset_id": first["dataset_id"], "checkpoint_name": "checkpoint", "initial_capital": 100})
    inference.upsert_step({"session_id": "session_1", "step_number": 1, "bet_amount": 1, "predicted_action": 0, "capital_after": 99})
    with database.Session() as session:
        assert session.execute(text("SELECT COUNT(*) FROM inference_session_steps")).scalar_one() == 1
    datasets.delete(first["dataset_id"])
    with database.Session() as session:
        assert session.execute(text("SELECT COUNT(*) FROM inference_sessions")).scalar_one() == 0
        assert session.execute(text("SELECT COUNT(*) FROM inference_session_steps")).scalar_one() == 0
