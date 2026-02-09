from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


###############################################################################
class RouletteSeries(Base):
    __tablename__ = "roulette_series"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    outcome = Column(Integer)
    color = Column(String)
    color_code = Column(Integer)
    position = Column(Integer)
    __table_args__ = (UniqueConstraint("name", "outcome"),)


###############################################################################
class InferenceContext(Base):
    __tablename__ = "inference_context"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    outcome = Column(Integer)
    uploaded_at = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint("name", "outcome"),)


###############################################################################
class GameSessions(Base):
    __tablename__ = "game_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String)
    step_id = Column(Integer)
    name = Column(String)
    checkpoint = Column(String)
    initial_capital = Column(Integer)
    bet_amount = Column(Integer)
    predicted_action = Column(Integer)
    predicted_action_desc = Column(String)
    predicted_confidence = Column(Float)
    observed_outcome = Column(Integer)
    reward = Column(Float)
    capital_after = Column(Float)
    timestamp = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint("session_id", "step_id"),)


###############################################################################
