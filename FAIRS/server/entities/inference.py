from __future__ import annotations

from pydantic import BaseModel, Field


###############################################################################
class InferenceStartRequest(BaseModel):
    checkpoint: str = Field(..., min_length=1)
    dataset_id: int = Field(..., ge=1)
    dataset_source: str | None = None
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
    bet_amount: int = Field(..., ge=1)


###############################################################################
class InferenceShutdownResponse(BaseModel):
    session_id: str
    status: str
