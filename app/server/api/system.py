from __future__ import annotations

import os

from fastapi import APIRouter, status

from server.common.constants import FASTAPI_VERSION
from server.contracts.system import HealthResponse

router = APIRouter(tags=["system"])

###############################################################################
@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
def health() -> HealthResponse:
    mode = "desktop" if os.getenv("FAIRS_TAURI_MODE", "").lower() == "true" else "development"
    return HealthResponse(
        status="ok",
        application="FAIRS",
        version=FASTAPI_VERSION,
        mode=mode,
    )
