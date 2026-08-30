from __future__ import annotations

from fastapi import APIRouter, status

from server.common.version import get_application_version
from server.contracts.system import HealthResponse

router = APIRouter(tags=["system"])


###############################################################################
@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        application="FAIRS",
        version=get_application_version(),
    )
