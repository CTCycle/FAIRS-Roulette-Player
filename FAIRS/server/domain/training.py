from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_CHECKPOINT_NAME_LENGTH = 128


###############################################################################
def normalize_checkpoint_identifier(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("Checkpoint name cannot be empty.")
    if len(candidate) > MAX_CHECKPOINT_NAME_LENGTH:
        raise ValueError("Checkpoint name is too long.")
    if candidate in {".", ".."}:
        raise ValueError("Invalid checkpoint name.")
    if any(ord(char) < 32 for char in candidate):
        raise ValueError("Checkpoint name contains invalid control characters.")
    if any(separator in candidate for separator in ("/", "\\", ":")):
        raise ValueError("Invalid checkpoint name.")
    if os.path.basename(candidate) != candidate:
        raise ValueError("Invalid checkpoint name.")
    return candidate


###############################################################################
class TrainingConfig(BaseModel):
    """Configuration for starting a new training session."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    # Agent parameters
    perceptive_field_size: int = Field(64, ge=1, le=1024)
    qnet_neurons: int = Field(64, ge=1, le=10000)
    embedding_dimensions: int = Field(200, ge=8)
    exploration_rate: float = Field(0.75, ge=0.0, le=1.0)
    exploration_rate_decay: float = Field(0.995, ge=0.0, le=1.0)
    minimum_exploration_rate: float = Field(0.10, ge=0.0, le=1.0)
    discount_rate: float = Field(0.50, ge=0.0, le=1.0)
    model_update_frequency: int = Field(10, ge=1)

    # Environment parameters
    bet_amount: int = Field(10, ge=1)
    initial_capital: int = Field(1000, ge=1)
    dynamic_betting_enabled: bool = False
    bet_strategy_model_enabled: bool = False
    bet_strategy_fixed_id: int = Field(0, ge=0, le=4)
    strategy_hold_steps: int = Field(1, ge=1)
    bet_unit: int | None = Field(None, ge=1)
    bet_max: int | None = Field(None, ge=1)
    bet_enforce_capital: bool = True

    # Dataset parameters
    dataset_id: int | None = Field(None, ge=1)
    use_data_generator: bool = False
    num_generated_samples: int = Field(10000, ge=100)
    sample_size: float = Field(1.0, gt=0.0, le=1.0)
    validation_size: float = Field(0.2, ge=0.0, lt=1.0)
    seed: int = 42

    # Session parameters
    episodes: int = Field(10, ge=1)
    max_steps_episode: int = Field(2000, ge=100)
    batch_size: int = Field(32, ge=1)
    learning_rate: float = Field(0.0001, gt=0.0)
    max_memory_size: int = Field(10000, ge=100)
    replay_buffer_size: int = Field(1000, ge=100)
    training_seed: int = 42
    checkpoint_name: str | None = Field(None, max_length=MAX_CHECKPOINT_NAME_LENGTH)

    # Device parameters
    use_device_gpu: bool = False
    device_id: int = Field(0, ge=0)
    use_mixed_precision: bool = False
    jit_compile: bool = False
    jit_backend: str = Field("inductor", min_length=1)

    # -------------------------------------------------------------------------
    @field_validator("checkpoint_name")
    @classmethod
    def validate_checkpoint_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value:
            return None
        return normalize_checkpoint_identifier(value)


###############################################################################
class ResumeConfig(BaseModel):
    """Configuration for resuming a training session from a checkpoint."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    checkpoint: str = Field(..., min_length=1, max_length=MAX_CHECKPOINT_NAME_LENGTH)
    additional_episodes: int = Field(10, ge=1)

    # -------------------------------------------------------------------------
    @field_validator("checkpoint")
    @classmethod
    def validate_checkpoint(cls, value: str) -> str:
        return normalize_checkpoint_identifier(value)
