from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
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
from sqlalchemy.orm import declarative_base

Base = declarative_base()


###############################################################################
class RouletteOutcomes(Base):
    __tablename__ = "roulette_outcomes"
    outcome_id = Column(SmallInteger, primary_key=True)
    color = Column(String, nullable=False)
    color_code = Column(SmallInteger, nullable=False)
    wheel_position = Column(SmallInteger, nullable=False, unique=True)
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
    dataset_id = Column(String(32), primary_key=True)
    dataset_name = Column(String, nullable=False)
    dataset_kind = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
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
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(
        String(32),
        ForeignKey("datasets.dataset_id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_index = Column(Integer, nullable=False)
    outcome_id = Column(
        SmallInteger,
        ForeignKey("roulette_outcomes.outcome_id"),
        nullable=False,
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
    session_id = Column(String(32), primary_key=True)
    dataset_id = Column(String(32), ForeignKey("datasets.dataset_id"), nullable=False)
    checkpoint_name = Column(String, nullable=False)
    initial_capital = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=False, default=func.now())
    ended_at = Column(DateTime)
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
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(32),
        ForeignKey("inference_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number = Column(Integer, nullable=False)
    bet_amount = Column(Integer, nullable=False)
    predicted_action = Column(Integer, nullable=False)
    predicted_confidence = Column(Float)
    observed_outcome_id = Column(
        SmallInteger,
        ForeignKey("roulette_outcomes.outcome_id"),
    )
    reward = Column(Float)
    capital_after = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=func.now())
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


