from __future__ import annotations

from pydantic import BaseModel


###############################################################################
class HealthResponse(BaseModel):
    status: str
    application: str
    version: str


###############################################################################
class RootStatusResponse(BaseModel):
    status: str
