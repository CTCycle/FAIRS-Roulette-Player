from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, update

from server.repositories.database.backend import FAIRSDatabase
from server.repositories.schemas.models import InferenceSessionSteps, InferenceSessions


###############################################################################
class InferenceRepository:
    # -------------------------------------------------------------------------
    def __init__(self, database: FAIRSDatabase) -> None:
        self.database = database

    # -------------------------------------------------------------------------
    def upsert_session(self, row: dict[str, Any]) -> None:
        values = {
            key: value
            for key, value in row.items()
            if key
            in {
                "session_id",
                "dataset_id",
                "checkpoint_name",
                "initial_capital",
                "started_at",
                "ended_at",
            }
        }
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
        values = {
            key: value
            for key, value in row.items()
            if key
            in {
                "session_id",
                "step_number",
                "bet_amount",
                "predicted_action",
                "predicted_confidence",
                "observed_outcome_id",
                "reward",
                "capital_after",
                "recorded_at",
            }
        }
        values.setdefault("recorded_at", datetime.now(timezone.utc))
        with self.database.transaction() as session:
            existing = session.get(
                InferenceSessionSteps, (values["session_id"], values["step_number"])
            )
            if existing is None:
                session.add(InferenceSessionSteps(**values))
            else:
                for key, value in values.items():
                    if key not in {"session_id", "step_number"}:
                        setattr(existing, key, value)

    # -------------------------------------------------------------------------
    def create_session_with_initial_step(
        self,
        session_row: dict[str, Any],
        step_row: dict[str, Any],
    ) -> None:
        session_values = {
            key: value
            for key, value in session_row.items()
            if key
            in {
                "session_id",
                "dataset_id",
                "checkpoint_name",
                "initial_capital",
                "started_at",
                "ended_at",
            }
        }
        step_values = {
            key: value
            for key, value in step_row.items()
            if key
            in {
                "session_id",
                "step_number",
                "bet_amount",
                "predicted_action",
                "predicted_confidence",
                "observed_outcome_id",
                "reward",
                "capital_after",
                "recorded_at",
            }
        }
        with self.database.transaction() as session:
            session.add(InferenceSessions(**session_values))
            session.add(InferenceSessionSteps(**step_values))

    # -------------------------------------------------------------------------
    def list_steps(self, session_id: str) -> list[dict[str, Any]]:
        with self.database.Session() as session:
            rows = session.scalars(
                select(InferenceSessionSteps)
                .where(InferenceSessionSteps.session_id == session_id)
                .order_by(InferenceSessionSteps.step_number)
            ).all()
            return [
                {
                    "step_number": row.step_number,
                    "bet_amount": row.bet_amount,
                    "predicted_action": row.predicted_action,
                    "predicted_confidence": row.predicted_confidence,
                    "observed_outcome_id": row.observed_outcome_id,
                    "reward": row.reward,
                    "capital_after": row.capital_after,
                    "recorded_at": row.recorded_at,
                }
                for row in rows
            ]

    # -------------------------------------------------------------------------
    def end_session(self, session_id: str) -> None:
        with self.database.transaction() as session:
            session.execute(
                update(InferenceSessions)
                .where(InferenceSessions.session_id == session_id)
                .values(ended_at=datetime.now(timezone.utc))
            )

    # -------------------------------------------------------------------------
    def restore_session(self, session_id: str) -> None:
        """Undo an eviction marker when a multi-session eviction fails."""
        with self.database.transaction() as session:
            session.execute(
                update(InferenceSessions)
                .where(InferenceSessions.session_id == session_id)
                .values(ended_at=None)
            )

    # -------------------------------------------------------------------------
    def clear_steps(self, session_id: str) -> None:
        with self.database.transaction() as session:
            session.execute(
                delete(InferenceSessionSteps).where(
                    InferenceSessionSteps.session_id == session_id
                )
            )

    # -------------------------------------------------------------------------
    def delete_session(self, session_id: str) -> None:
        with self.database.transaction() as session:
            session.execute(
                delete(InferenceSessions).where(
                    InferenceSessions.session_id == session_id
                )
            )
