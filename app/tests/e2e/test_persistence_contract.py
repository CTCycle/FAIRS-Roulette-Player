from __future__ import annotations

import os

import pandas as pd
import pytest
from sqlalchemy import create_engine, event, text

from server.repositories.database.backend import FAIRSDatabase
from server.repositories.datasets import DatasetRepository
from server.repositories.inference import InferenceRepository


###############################################################################
def exercise_contract(database: FAIRSDatabase) -> None:
    database.create_schema()
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
    exercise_contract(FAIRSDatabase(engine=engine))


###############################################################################
@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="PostgreSQL contract requires TEST_POSTGRES_URL")
def test_postgresql_contract() -> None:
    engine = create_engine(os.environ["TEST_POSTGRES_URL"], pool_pre_ping=True)
    exercise_contract(FAIRSDatabase(engine=engine))
