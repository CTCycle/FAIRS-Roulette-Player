from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from FAIRS.server.configurations.dependencies import get_inference_service
from FAIRS.server.domain.inference import (
    InferenceBetUpdateRequest,
    InferenceBetUpdateResponse,
    InferenceContextClearResponse,
    InferenceNextResponse,
    InferenceRowsClearResponse,
    InferenceShutdownResponse,
    InferenceStartRequest,
    InferenceStartResponse,
    InferenceStepRequest,
    InferenceStepResponse,
)
from FAIRS.server.services.inference import InferenceService

router = APIRouter(prefix="/inference", tags=["inference"])

###############################################################################
def _map_inference_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, RuntimeError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if isinstance(exc, ValueError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    if isinstance(exc, FileNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    if isinstance(exc, KeyError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to process inference request.",
    )


###############################################################################
@router.post(
    "/sessions/start",
    status_code=status.HTTP_200_OK,
)
def start_session(
    payload: InferenceStartRequest,
    service: Annotated[InferenceService, Depends(get_inference_service)],
) -> InferenceStartResponse:
    try:
        return InferenceStartResponse.model_validate(service.start_session(payload))
    except Exception as exc:
        raise _map_inference_exception(exc) from exc


###############################################################################
@router.post(
    "/sessions/{session_id}/next",
    status_code=status.HTTP_200_OK,
)
def next_prediction(
    session_id: str,
    service: Annotated[InferenceService, Depends(get_inference_service)],
) -> InferenceNextResponse:
    try:
        return InferenceNextResponse.model_validate(service.next_prediction(session_id))
    except Exception as exc:
        raise _map_inference_exception(exc) from exc


###############################################################################
@router.post(
    "/sessions/{session_id}/step",
    status_code=status.HTTP_200_OK,
)
def submit_step(
    session_id: str,
    payload: InferenceStepRequest,
    service: Annotated[InferenceService, Depends(get_inference_service)],
) -> InferenceStepResponse:
    try:
        return InferenceStepResponse.model_validate(service.step_session(session_id, payload))
    except Exception as exc:
        raise _map_inference_exception(exc) from exc


###############################################################################
@router.post(
    "/sessions/{session_id}/shutdown",
    status_code=status.HTTP_200_OK,
)
def shutdown(
    session_id: str,
    service: Annotated[InferenceService, Depends(get_inference_service)],
) -> InferenceShutdownResponse:
    return InferenceShutdownResponse.model_validate(service.shutdown_session(session_id))


###############################################################################
@router.post(
    "/sessions/{session_id}/bet",
    status_code=status.HTTP_200_OK,
)
def update_bet_amount(
    session_id: str,
    payload: InferenceBetUpdateRequest,
    service: Annotated[InferenceService, Depends(get_inference_service)],
) -> InferenceBetUpdateResponse:
    try:
        return InferenceBetUpdateResponse.model_validate(service.update_bet(session_id, payload))
    except Exception as exc:
        raise _map_inference_exception(exc) from exc


###############################################################################
@router.post(
    "/sessions/{session_id}/rows/clear",
    status_code=status.HTTP_200_OK,
)
def clear_session_rows(
    session_id: str,
    service: Annotated[InferenceService, Depends(get_inference_service)],
) -> InferenceRowsClearResponse:
    return InferenceRowsClearResponse.model_validate(service.clear_session_rows(session_id))


###############################################################################
@router.post(
    "/context/clear",
    status_code=status.HTTP_200_OK,
)
def clear_inference_context(
    service: Annotated[InferenceService, Depends(get_inference_service)],
) -> InferenceContextClearResponse:
    return InferenceContextClearResponse.model_validate(service.clear_context())
