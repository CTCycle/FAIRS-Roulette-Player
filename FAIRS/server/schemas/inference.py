from __future__ import annotations

from pydantic import BaseModel, Field


###############################################################################
class InferenceStartRequest(BaseModel):
    checkpoint: str = Field(..., min_length=1)
    dataset_name: str = Field(..., min_length=1)
    game_capital: int = Field(100, ge=1)
    game_bet: int = Field(1, ge=1)


###############################################################################
class PredictionResponse(BaseModel):
    action: int
    description: str
    confidence: float | None = None


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
    next_prediction: PredictionResponse


###############################################################################
class InferenceShutdownResponse(BaseModel):
    session_id: str
    status: str

