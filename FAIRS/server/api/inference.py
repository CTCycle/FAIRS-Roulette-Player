from __future__ import annotations

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
    response_model=InferenceStartResponse,
    status_code=status.HTTP_200_OK,
)
def start_session(
    payload: InferenceStartRequest,
    service: InferenceService = Depends(get_inference_service),
) -> InferenceStartResponse:
    try:
        return InferenceStartResponse.model_validate(service.start_session(payload))
    except Exception as exc:
        raise _map_inference_exception(exc) from exc


###############################################################################
@router.post(
    "/sessions/{session_id}/next",
    response_model=InferenceNextResponse,
    status_code=status.HTTP_200_OK,
)
def next_prediction(
    session_id: str,
    service: InferenceService = Depends(get_inference_service),
) -> InferenceNextResponse:
    try:
        return InferenceNextResponse.model_validate(service.next_prediction(session_id))
    except Exception as exc:
        raise _map_inference_exception(exc) from exc


###############################################################################
@router.post(
    "/sessions/{session_id}/step",
    response_model=InferenceStepResponse,
    status_code=status.HTTP_200_OK,
)
def submit_step(
    session_id: str,
    payload: InferenceStepRequest,
    service: InferenceService = Depends(get_inference_service),
) -> InferenceStepResponse:
    try:
        return InferenceStepResponse.model_validate(service.step_session(session_id, payload))
    except Exception as exc:
        raise _map_inference_exception(exc) from exc


###############################################################################
@router.post(
    "/sessions/{session_id}/shutdown",
    response_model=InferenceShutdownResponse,
    status_code=status.HTTP_200_OK,
)
def shutdown(
    session_id: str,
    service: InferenceService = Depends(get_inference_service),
) -> InferenceShutdownResponse:
    return InferenceShutdownResponse.model_validate(service.shutdown_session(session_id))


###############################################################################
@router.post(
    "/sessions/{session_id}/bet",
    response_model=InferenceBetUpdateResponse,
    status_code=status.HTTP_200_OK,
)
def update_bet_amount(
    session_id: str,
    payload: InferenceBetUpdateRequest,
    service: InferenceService = Depends(get_inference_service),
) -> InferenceBetUpdateResponse:
    try:
        return InferenceBetUpdateResponse.model_validate(service.update_bet(session_id, payload))
    except Exception as exc:
        raise _map_inference_exception(exc) from exc


###############################################################################
@router.post(
    "/sessions/{session_id}/rows/clear",
    response_model=InferenceRowsClearResponse,
    status_code=status.HTTP_200_OK,
)
def clear_session_rows(
    session_id: str,
    service: InferenceService = Depends(get_inference_service),
) -> InferenceRowsClearResponse:
    return InferenceRowsClearResponse.model_validate(service.clear_session_rows(session_id))


###############################################################################
@router.post(
    "/context/clear",
    response_model=InferenceContextClearResponse,
    status_code=status.HTTP_200_OK,
)
def clear_inference_context(
    service: InferenceService = Depends(get_inference_service),
) -> InferenceContextClearResponse:
    return InferenceContextClearResponse.model_validate(service.clear_context())
