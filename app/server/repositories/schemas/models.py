from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from server.common.checkpoints import MAX_CHECKPOINT_NAME_LENGTH
from server.common.session import MAX_SESSION_ID_LENGTH

###############################################################################
class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    # -------------------------------------------------------------------------
    def process_bind_param(self, value: datetime | None, _dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    # -------------------------------------------------------------------------
    def process_result_value(self, value: datetime | None, _dialect: Any) -> datetime | None:
        if value is None:
            return None
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)

###############################################################################
class Base(DeclarativeBase):
    pass

###############################################################################
class Datasets(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_name_key: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    outcomes: Mapped[list[DatasetOutcomes]] = relationship(back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True, lazy="raise")
    inference_sessions: Mapped[list[InferenceSessions]] = relationship(back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True, lazy="raise")
    __table_args__ = (
        UniqueConstraint("dataset_kind", "dataset_name_key", name="uq_datasets_kind_name_key"),
        Index("ix_datasets_kind_name", "dataset_kind", "dataset_name_key"),
        CheckConstraint("dataset_kind IN ('training', 'inference')", name="ck_datasets_kind"),
    )

###############################################################################
class DatasetOutcomes(Base):
    __tablename__ = "dataset_outcomes"

    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.dataset_id", ondelete="CASCADE"), primary_key=True)
    sequence_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    outcome_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    dataset: Mapped[Datasets] = relationship(back_populates="outcomes", lazy="raise")
    __table_args__ = (
        CheckConstraint("sequence_index >= 0", name="ck_dataset_outcomes_sequence"),
        CheckConstraint("outcome_id >= 0 AND outcome_id <= 36", name="ck_dataset_outcomes_outcome"),
        Index("ix_dataset_outcomes_dataset_outcome", "dataset_id", "outcome_id"),
    )

###############################################################################
class InferenceSessions(Base):
    __tablename__ = "inference_sessions"

    session_id: Mapped[str] = mapped_column(String(MAX_SESSION_ID_LENGTH), primary_key=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.dataset_id", ondelete="CASCADE"), nullable=False)
    checkpoint_name: Mapped[str] = mapped_column(String(MAX_CHECKPOINT_NAME_LENGTH), nullable=False)
    initial_capital: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    dataset: Mapped[Datasets] = relationship(back_populates="inference_sessions", lazy="raise")
    steps: Mapped[list[InferenceSessionSteps]] = relationship(back_populates="session", cascade="all, delete-orphan", passive_deletes=True, lazy="raise")
    __table_args__ = (
        CheckConstraint("initial_capital > 0", name="ck_inference_sessions_initial_capital"),
        Index("ix_inference_sessions_dataset_started", "dataset_id", "started_at"),
    )

###############################################################################
class InferenceSessionSteps(Base):
    __tablename__ = "inference_session_steps"

    session_id: Mapped[str] = mapped_column(String(MAX_SESSION_ID_LENGTH), ForeignKey("inference_sessions.session_id", ondelete="CASCADE"), primary_key=True)
    step_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    bet_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_action: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_confidence: Mapped[float | None] = mapped_column(Float)
    observed_outcome_id: Mapped[int | None] = mapped_column(SmallInteger)
    reward: Mapped[int | None] = mapped_column(Integer)
    capital_after: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=lambda: datetime.now(timezone.utc))
    session: Mapped[InferenceSessions] = relationship(back_populates="steps", lazy="raise")
    __table_args__ = (
        CheckConstraint("step_number > 0", name="ck_inference_steps_step_number"),
        CheckConstraint("bet_amount > 0", name="ck_inference_steps_bet_amount"),
        CheckConstraint("predicted_action >= 0 AND predicted_action <= 46", name="ck_inference_steps_action"),
        CheckConstraint("observed_outcome_id IS NULL OR (observed_outcome_id >= 0 AND observed_outcome_id <= 36)", name="ck_inference_steps_observed_outcome"),
        CheckConstraint("predicted_confidence IS NULL OR (predicted_confidence >= 0 AND predicted_confidence <= 1)", name="ck_inference_steps_confidence"),
        Index("ix_inference_steps_session_recorded", "session_id", "recorded_at"),
    )
