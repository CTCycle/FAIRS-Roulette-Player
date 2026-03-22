from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


###############################################################################
class Base(DeclarativeBase):
    pass


###############################################################################
class RouletteOutcomes(Base):
    __tablename__ = "roulette_outcomes"
    outcome_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    color: Mapped[str] = mapped_column(String, nullable=False)
    color_code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    wheel_position: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        unique=True,
    )
    dataset_outcomes: Mapped[list[DatasetOutcomes]] = relationship(
        back_populates="roulette_outcome"
    )
    inference_session_steps: Mapped[list[InferenceSessionSteps]] = relationship(
        back_populates="observed_outcome"
    )
    __table_args__ = (
        CheckConstraint(
            "outcome_id >= 0 AND outcome_id <= 36",
            name="ck_roulette_outcomes_outcome_range",
        ),
        CheckConstraint(
            "color IN ('green', 'black', 'red')",
            name="ck_roulette_outcomes_color",
        ),
        CheckConstraint(
            "color_code IN (0, 1, 2)",
            name="ck_roulette_outcomes_color_code",
        ),
        CheckConstraint(
            "wheel_position >= 0 AND wheel_position <= 36",
            name="ck_roulette_outcomes_wheel_pos",
        ),
    )


###############################################################################
class Datasets(Base):
    __tablename__ = "datasets"
    dataset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_name: Mapped[str] = mapped_column(String, nullable=False)
    dataset_kind: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[Any] = mapped_column(DateTime, nullable=False, default=func.now())
    outcomes: Mapped[list[DatasetOutcomes]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    inference_sessions: Mapped[list[InferenceSessions]] = relationship(
        back_populates="dataset"
    )
    __table_args__ = (
        UniqueConstraint("dataset_kind", "dataset_name"),
        CheckConstraint(
            "dataset_kind IN ('training', 'inference')",
            name="ck_datasets_kind",
        ),
    )


###############################################################################
class DatasetOutcomes(Base):
    __tablename__ = "dataset_outcomes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("datasets.dataset_id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("roulette_outcomes.outcome_id"),
        nullable=False,
    )
    dataset: Mapped[Datasets] = relationship(back_populates="outcomes")
    roulette_outcome: Mapped[RouletteOutcomes] = relationship(
        back_populates="dataset_outcomes"
    )
    __table_args__ = (
        UniqueConstraint("dataset_id", "sequence_index"),
        CheckConstraint(
            "sequence_index >= 0",
            name="ck_dataset_outcomes_sequence",
        ),
        CheckConstraint(
            "outcome_id >= 0 AND outcome_id <= 36",
            name="ck_dataset_outcomes_outcome",
        ),
        Index("ix_dataset_outcomes_dataset_sequence", "dataset_id", "sequence_index"),
        Index("ix_dataset_outcomes_dataset_outcome", "dataset_id", "outcome_id"),
    )


###############################################################################
class InferenceSessions(Base):
    __tablename__ = "inference_sessions"
    session_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("datasets.dataset_id"),
        nullable=False,
    )
    checkpoint_name: Mapped[str] = mapped_column(String, nullable=False)
    initial_capital: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[Any] = mapped_column(DateTime, nullable=False, default=func.now())
    ended_at: Mapped[Any | None] = mapped_column(DateTime)
    dataset: Mapped[Datasets] = relationship(back_populates="inference_sessions")
    steps: Mapped[list[InferenceSessionSteps]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    __table_args__ = (
        CheckConstraint(
            "initial_capital > 0",
            name="ck_inference_sessions_initial_capital",
        ),
        Index("ix_inference_sessions_dataset_started", "dataset_id", "started_at"),
        Index("ix_inference_sessions_checkpoint", "checkpoint_name"),
    )


###############################################################################
class InferenceSessionSteps(Base):
    __tablename__ = "inference_session_steps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("inference_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bet_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_action: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_confidence: Mapped[float | None] = mapped_column(Float)
    observed_outcome_id: Mapped[int | None] = mapped_column(
        SmallInteger,
        ForeignKey("roulette_outcomes.outcome_id"),
    )
    reward: Mapped[float | None] = mapped_column(Float)
    capital_after: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[Any] = mapped_column(DateTime, nullable=False, default=func.now())
    session: Mapped[InferenceSessions] = relationship(back_populates="steps")
    observed_outcome: Mapped[RouletteOutcomes | None] = relationship(
        back_populates="inference_session_steps"
    )
    __table_args__ = (
        UniqueConstraint("session_id", "step_number"),
        CheckConstraint(
            "step_number > 0",
            name="ck_inference_steps_step_number",
        ),
        CheckConstraint(
            "bet_amount > 0",
            name="ck_inference_steps_bet_amount",
        ),
        CheckConstraint(
            "observed_outcome_id IS NULL OR "
            "(observed_outcome_id >= 0 AND observed_outcome_id <= 36)",
            name="ck_inference_steps_observed_outcome",
        ),
        CheckConstraint(
            "predicted_confidence IS NULL OR "
            "(predicted_confidence >= 0 AND predicted_confidence <= 1)",
            name="ck_inference_steps_confidence",
        ),
        Index("ix_inference_steps_session_recorded", "session_id", "recorded_at"),
        Index("ix_inference_steps_observed_outcome", "observed_outcome_id"),
    )


# -----------------------------------------------------------------------------
def iter_model_classes() -> Iterator[type[Any]]:
    for mapper in Base.registry.mappers:
        model_cls = mapper.class_
        if isinstance(model_cls, type):
            yield model_cls


# -----------------------------------------------------------------------------
def get_model_class_for_table(table_name: str) -> type[Any]:
    for model_cls in iter_model_classes():
        if getattr(model_cls, "__tablename__", None) == table_name:
            return model_cls
    raise ValueError(f"No table class found for name {table_name}")
