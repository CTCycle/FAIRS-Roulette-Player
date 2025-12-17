from __future__ import annotations

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
    id = Column(Integer, primary_key=True)
    extraction = Column(Integer)
    color = Column(String)
    color_code = Column(Integer)
    position = Column(Integer)
    __table_args__ = (UniqueConstraint("id"),)


###############################################################################
class PredictedGames(Base):
    __tablename__ = "PREDICTED_GAMES"
    id = Column(Integer, primary_key=True)
    checkpoint = Column(String)
    extraction = Column(Integer)
    predicted_action = Column(String)
    __table_args__ = (UniqueConstraint("id"),)


###############################################################################
class CheckpointSummary(Base):
    __tablename__ = "CHECKPOINTS_SUMMARY"
    checkpoint = Column(String, primary_key=True)
    sample_size = Column(Float)
    seed = Column(Integer)
    precision = Column(Integer)
    episodes = Column(Integer)
    max_steps_episode = Column(Integer)
    batch_size = Column(Integer)
    jit_compile = Column(String)
    has_tensorboard_logs = Column(String)
    learning_rate = Column(Float)
    neurons = Column(Integer)
    embedding_dimensions = Column(Integer)
    perceptive_field_size = Column(Integer)
    exploration_rate = Column(Float)
    exploration_rate_decay = Column(Float)
    discount_rate = Column(Float)
    model_update_frequency = Column(Integer)
    loss = Column(Float)
    accuracy = Column(Float)
    __table_args__ = (UniqueConstraint("checkpoint"),)