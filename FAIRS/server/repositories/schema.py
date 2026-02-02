from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


###############################################################################
class RouletteSeries(Base):
    __tablename__ = "ROULETTE_SERIES"
    dataset_name = Column(String, primary_key=True)
    id = Column(Integer, primary_key=True)
    extraction = Column(Integer)
    color = Column(String)
    color_code = Column(Integer)
    position = Column(Integer)
    __table_args__ = (UniqueConstraint("id", "dataset_name"),)


###############################################################################
class InferenceContext(Base):
    __tablename__ = "INFERENCE_CONTEXT"
    dataset_name = Column(String, primary_key=True)
    id = Column(Integer, primary_key=True)
    extraction = Column(Integer)
    uploaded_at = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint("id", "dataset_name"),)


###############################################################################
class GameSessions(Base):
    __tablename__ = "GAME_SESSIONS"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String)
    step_index = Column(Integer)
    dataset_name = Column(String)
    checkpoint = Column(String)
    initial_capital = Column(Integer)
    bet_amount = Column(Integer)
    predicted_action = Column(Integer)
    predicted_action_desc = Column(String)
    predicted_confidence = Column(Float)
    observed_extraction = Column(Integer)
    reward = Column(Float)
    capital_after = Column(Float)
    timestamp = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint("session_id", "step_index"),)


###############################################################################
