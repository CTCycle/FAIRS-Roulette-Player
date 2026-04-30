from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from server.common.checkpoints import (
    MAX_CHECKPOINT_NAME_LENGTH,
    normalize_checkpoint_identifier,
)

MAX_SESSION_ID_LENGTH = 64


###############################################################################
def normalize_session_id(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if len(candidate) > MAX_SESSION_ID_LENGTH:
        raise ValueError("Session identifier is too long.")
    if any(ord(char) < 32 for char in candidate):
        raise ValueError("Session identifier contains invalid control characters.")
    if any(
        not (char.isalnum() or char in {"-", "_"}) for char in candidate
    ):
        raise ValueError(
            "Session identifier can contain only letters, numbers, '-' and '_'."
        )
    return candidate


###############################################################################
class InferenceStartRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    checkpoint: str = Field(..., min_length=1, max_length=MAX_CHECKPOINT_NAME_LENGTH)
    dataset_id: int = Field(..., ge=1)
    dataset_source: str | None = Field(None, pattern="^(source|uploaded)$")
    session_id: str | None = None
    game_capital: int = Field(100, ge=1)
    game_bet: int = Field(1, ge=1)
    dynamic_betting_enabled: bool = False
    bet_strategy_model_enabled: bool = False
    bet_strategy_fixed_id: int = Field(0, ge=0, le=4)
    strategy_hold_steps: int = Field(1, ge=1)
    bet_unit: int | None = Field(None, ge=1)
    bet_max: int | None = Field(None, ge=1)
    bet_enforce_capital: bool = True
    auto_apply_bet_suggestions: bool = False

    # -------------------------------------------------------------------------
    @field_validator("checkpoint")
    @classmethod
    def validate_checkpoint(cls, value: str) -> str:
        return normalize_checkpoint_identifier(value)

    # -------------------------------------------------------------------------
    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        return normalize_session_id(value)


###############################################################################
class PredictionResponse(BaseModel):
    action: int
    description: str
    confidence: float | None = None
    bet_strategy_id: int | None = None
    bet_strategy_name: str | None = None
    suggested_bet_amount: int | None = None
    current_bet_amount: int | None = None


###############################################################################
class InferenceStartResponse(BaseModel):
    session_id: str
    checkpoint: str
    game_capital: int
    game_bet: int
    current_capital: int
    prediction: PredictionResponse


###############################################################################
class InferenceNextResponse(BaseModel):
    session_id: str
    prediction: PredictionResponse


###############################################################################
class InferenceStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction: int = Field(..., ge=0, le=36)


###############################################################################
class InferenceStepResponse(BaseModel):
    session_id: str
    step: int
    real_extraction: int
    predicted_action: int
    predicted_action_desc: str
    reward: int
    capital_after: int


###############################################################################
class InferenceBetUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bet_amount: int = Field(..., ge=1)


###############################################################################
class InferenceShutdownResponse(BaseModel):
    session_id: str
    status: str


###############################################################################
class InferenceBetUpdateResponse(BaseModel):
    session_id: str
    bet_amount: int


###############################################################################
class InferenceRowsClearResponse(BaseModel):
    session_id: str
    status: str


###############################################################################
class InferenceContextClearResponse(BaseModel):
    status: str
