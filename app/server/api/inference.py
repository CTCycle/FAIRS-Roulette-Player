from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from FAIRS.server.common.api_errors import (
    ExceptionStatusMap,
    http_exception_for_exception,
)
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

INFERENCE_EXCEPTION_STATUS: ExceptionStatusMap = (
    (RuntimeError, status.HTTP_409_CONFLICT),
    (ValueError, status.HTTP_400_BAD_REQUEST),
    (FileNotFoundError, status.HTTP_404_NOT_FOUND),
    (KeyError, status.HTTP_404_NOT_FOUND),
)

###############################################################################
def _map_inference_exception(exc: Exception) -> HTTPException:
    return http_exception_for_exception(
        exc,
        INFERENCE_EXCEPTION_STATUS,
        default_detail="Unable to process inference request.",
    )


###############################################################################
@router.post(
    "/sessions/start",
    response_model=InferenceStartResponse,
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
    response_model=InferenceNextResponse,
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
    response_model=InferenceStepResponse,
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
    response_model=InferenceShutdownResponse,
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
    response_model=InferenceBetUpdateResponse,
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
    response_model=InferenceRowsClearResponse,
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
    response_model=InferenceContextClearResponse,
    status_code=status.HTTP_200_OK,
)
def clear_inference_context(
    service: Annotated[InferenceService, Depends(get_inference_service)],
) -> InferenceContextClearResponse:
    return InferenceContextClearResponse.model_validate(service.clear_context())
