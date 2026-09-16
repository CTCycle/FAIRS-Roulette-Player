from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from server.common.api_errors import (
    ExceptionStatusMap,
    http_exception_for_exception,
)
from server.common.roulette import validate_roulette_outcome
from server.configurations.dependencies import get_inference_service, get_settings_service
from server.contracts.configuration import RouletteSettings
from server.contracts.inference import (
    InferenceBetUpdateRequest,
    InferenceBetUpdateResponse,
    InferenceContextClearResponse,
    InferenceNextResponse,
    InferenceRowsClearResponse,
    InferenceSessionStatusResponse,
    InferenceShutdownResponse,
    InferenceStartRequest,
    InferenceStartResponse,
    InferenceStepRequest,
    InferenceStepResponse,
)
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
def _roulette_settings(settings_service: Any) -> RouletteSettings:
    settings = settings_service.get_settings().roulette
    return RouletteSettings(
        minimum_number=settings.minimum_number,
        maximum_number=settings.maximum_number,
        exclude_zero=settings.exclude_zero,
        invert_colors=settings.invert_colors,
        show_number_labels=settings.show_number_labels,
    )

###############################################################################
@router.post(
    "/sessions/start",
    response_model=InferenceStartResponse,
    status_code=status.HTTP_200_OK,
)
def start_session(
    payload: InferenceStartRequest,
    service: Annotated[Any, Depends(get_inference_service)],
    settings_service: Annotated[Any, Depends(get_settings_service)],
    preserve_session_id: Annotated[
        str | None,
        Header(alias="X-Preserve-Inference-Session"),
    ] = None,
) -> InferenceStartResponse:
    try:
        roulette_settings = _roulette_settings(settings_service)
        if preserve_session_id is None:
            result = service.start_session(
                payload,
                roulette_settings=roulette_settings,
            )
        else:
            result = service.start_session(
                payload,
                preserve_session_id=preserve_session_id,
                roulette_settings=roulette_settings,
            )
        return InferenceStartResponse.model_validate(
            result
        )
    except Exception as exc:
        raise _map_inference_exception(exc) from exc

###############################################################################
@router.get(
    "/sessions/{session_id}",
    response_model=InferenceSessionStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_session(
    session_id: str,
    service: Annotated[Any, Depends(get_inference_service)],
) -> InferenceSessionStatusResponse:
    try:
        return InferenceSessionStatusResponse.model_validate(
            service.get_session_snapshot(session_id)
        )
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
    service: Annotated[Any, Depends(get_inference_service)],
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
    service: Annotated[Any, Depends(get_inference_service)],
    settings_service: Annotated[Any, Depends(get_settings_service)],
) -> InferenceStepResponse:
    try:
        roulette_settings = settings_service.get_settings().roulette
        validate_roulette_outcome(
            payload.extraction,
            minimum_number=roulette_settings.minimum_number,
            maximum_number=roulette_settings.maximum_number,
            exclude_zero=roulette_settings.exclude_zero,
        )
        return InferenceStepResponse.model_validate(
            service.step_session(session_id, payload)
        )
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
    service: Annotated[Any, Depends(get_inference_service)],
) -> InferenceShutdownResponse:
    try:
        return InferenceShutdownResponse.model_validate(
            service.shutdown_session(session_id)
        )
    except Exception as exc:
        raise _map_inference_exception(exc) from exc

###############################################################################
@router.post(
    "/sessions/{session_id}/bet",
    response_model=InferenceBetUpdateResponse,
    status_code=status.HTTP_200_OK,
)
def update_bet_amount(
    session_id: str,
    payload: InferenceBetUpdateRequest,
    service: Annotated[Any, Depends(get_inference_service)],
) -> InferenceBetUpdateResponse:
    try:
        return InferenceBetUpdateResponse.model_validate(
            service.update_bet(session_id, payload)
        )
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
    service: Annotated[Any, Depends(get_inference_service)],
) -> InferenceRowsClearResponse:
    try:
        return InferenceRowsClearResponse.model_validate(
            service.clear_session_rows(session_id)
        )
    except Exception as exc:
        raise _map_inference_exception(exc) from exc

###############################################################################
@router.post(
    "/context/clear",
    response_model=InferenceContextClearResponse,
    status_code=status.HTTP_200_OK,
)
def clear_inference_context(
    service: Annotated[Any, Depends(get_inference_service)],
) -> InferenceContextClearResponse:
    try:
        return InferenceContextClearResponse.model_validate(service.clear_context())
    except Exception as exc:
        raise _map_inference_exception(exc) from exc