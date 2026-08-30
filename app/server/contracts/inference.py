from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from server.common.checkpoints import (
    MAX_CHECKPOINT_NAME_LENGTH,
    normalize_checkpoint_identifier,
)


###############################################################################
class InferenceStartRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    checkpoint: str = Field(..., min_length=1, max_length=MAX_CHECKPOINT_NAME_LENGTH)
    dataset_id: StrictInt = Field(..., ge=1)
    game_capital: int = Field(100, ge=1)
    game_bet: int = Field(1, ge=1)

    # -------------------------------------------------------------------------
    @field_validator("checkpoint")
    @classmethod
    def validate_checkpoint(cls, value: str) -> str:
        return normalize_checkpoint_identifier(value)


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
