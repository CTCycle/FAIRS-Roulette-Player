from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from server.common.utils.logger import logger
from server.configurations.dependencies import get_settings_service
from server.contracts.settings import SettingsPatchRequest, SettingsResponse
from server.services.settings import SettingsPersistenceError

router = APIRouter(prefix="/settings", tags=["settings"])

###############################################################################
def _settings_failure(detail: str, exc: Exception) -> HTTPException:
    logger.exception("%s", detail, exc_info=exc)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

###############################################################################
@router.get(
    "",
    response_model=SettingsResponse,
    status_code=status.HTTP_200_OK,
)
def get_settings(
    service: Any = Depends(get_settings_service),
) -> SettingsResponse:
    try:
        return service.get_settings()
    except Exception as exc:  # noqa: BLE001
        raise _settings_failure("Unable to load settings.", exc) from exc

###############################################################################
@router.patch(
    "",
    response_model=SettingsResponse,
    status_code=status.HTTP_200_OK,
)
def update_settings(
    patch: SettingsPatchRequest,
    service: Any = Depends(get_settings_service),
) -> SettingsResponse:
    try:
        return service.update_settings(patch)
    except SettingsPersistenceError as exc:
        raise _settings_failure("Unable to save settings.", exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise _settings_failure("Unable to save settings.", exc) from exc

###############################################################################
@router.post(
    "/reset",
    response_model=SettingsResponse,
    status_code=status.HTTP_200_OK,
)
def reset_settings(
    service: Any = Depends(get_settings_service),
) -> SettingsResponse:
    try:
        return service.reset_settings()
    except SettingsPersistenceError as exc:
        raise _settings_failure("Unable to save settings.", exc) from exc
    except Exception as exc:  # noqa: BLE001
        raise _settings_failure("Unable to save settings.", exc) from exc
