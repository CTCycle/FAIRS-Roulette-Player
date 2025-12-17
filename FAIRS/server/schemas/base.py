from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, Field

###############################################################################
class GeneralModel(BaseModel):
    param_A: float = Field(..., ge=-90.0, le=90.0)
    param_B: float = Field(..., ge=-180.0, le=180.0)
