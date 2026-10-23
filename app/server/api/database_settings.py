# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, status

from server.configurations.dependencies import get_database_configuration_service
from server.contracts.database_configuration import (
    DatabaseConfigurationInput,
    DatabaseStatusResponse,
    DatabaseTestResponse,
)
from server.services.database_configuration import (
    DatabaseConfigurationService,
    DatabaseSwitchConflict,
    DatabaseSwitchError,
)

router = APIRouter(prefix="/settings/database", tags=["database settings"])

###############################################################################
@router.get("", response_model=DatabaseStatusResponse)
def get_database_settings(
    service: DatabaseConfigurationService = Depends(get_database_configuration_service),
) -> DatabaseStatusResponse:
    return service.get_status()

###############################################################################
@router.post("/test", response_model=DatabaseTestResponse)
def test_database_connection(
    candidate: DatabaseConfigurationInput,
    service: DatabaseConfigurationService = Depends(get_database_configuration_service),
) -> DatabaseTestResponse:
    return service.test_connection(candidate)

###############################################################################
@router.put("", response_model=DatabaseStatusResponse)
def update_database_settings(
    candidate: DatabaseConfigurationInput,
    service: DatabaseConfigurationService = Depends(get_database_configuration_service),
) -> DatabaseStatusResponse:
    try:
        return service.activate(candidate)
    except DatabaseSwitchConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DatabaseSwitchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
