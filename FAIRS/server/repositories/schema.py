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
class PredictedGames(Base):
    __tablename__ = "PREDICTED_GAMES"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String)
    dataset_name = Column(String)
    checkpoint = Column(String)
    extraction = Column(Integer)
    predicted_action = Column(String)
    timestamp = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint("id"),)


###############################################################################
