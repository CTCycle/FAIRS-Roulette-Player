# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

from fastapi import APIRouter, Request, status

from server.common.version import get_application_version
from server.contracts.system import HealthResponse

router = APIRouter(tags=["system"])


###############################################################################
@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status=(
            "recovery"
            if getattr(request.app.state, "lifecycle", "starting") == "recovery"
            else "ok"
        ),
        application="FAIRS",
        version=get_application_version(),
    )
