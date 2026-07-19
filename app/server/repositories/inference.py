from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, update

from server.repositories.database.backend import FAIRSDatabase
from server.repositories.schemas.models import InferenceSessionSteps, InferenceSessions

###############################################################################
class InferenceRepository:

    # -------------------------------------------------------------------------
    def __init__(self, database: FAIRSDatabase) -> None:
        self.database = database

    # -------------------------------------------------------------------------
    def upsert_session(self, row: dict[str, Any]) -> None:
        values = {key: value for key, value in row.items() if key in {"session_id", "dataset_id", "checkpoint_name", "initial_capital", "started_at", "ended_at"}}
        values.setdefault("started_at", datetime.now(timezone.utc))
        with self.database.transaction() as session:
            existing = session.get(InferenceSessions, values["session_id"])
            if existing is None:
                session.add(InferenceSessions(**values))
            else:
                for key, value in values.items():
                    if key != "session_id":
                        setattr(existing, key, value)

    # -------------------------------------------------------------------------
    def upsert_step(self, row: dict[str, Any]) -> None:
        values = {key: value for key, value in row.items() if key in {"session_id", "step_number", "bet_amount", "predicted_action", "predicted_confidence", "observed_outcome_id", "reward", "capital_after", "recorded_at"}}
        values.setdefault("recorded_at", datetime.now(timezone.utc))
        with self.database.transaction() as session:
            existing = session.get(InferenceSessionSteps, (values["session_id"], values["step_number"]))
            if existing is None:
                session.add(InferenceSessionSteps(**values))
            else:
                for key, value in values.items():
                    if key not in {"session_id", "step_number"}:
                        setattr(existing, key, value)

    # -------------------------------------------------------------------------
    def end_session(self, session_id: str) -> None:
        with self.database.transaction() as session:
            session.execute(update(InferenceSessions).where(InferenceSessions.session_id == session_id).values(ended_at=datetime.now(timezone.utc)))

    # -------------------------------------------------------------------------
    def clear_steps(self, session_id: str) -> None:
        with self.database.transaction() as session:
            session.execute(delete(InferenceSessionSteps).where(InferenceSessionSteps.session_id == session_id))

    # -------------------------------------------------------------------------
    def delete_session(self, session_id: str) -> None:
        with self.database.transaction() as session:
            session.execute(delete(InferenceSessions).where(InferenceSessions.session_id == session_id))
