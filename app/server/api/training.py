from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from server.common.api_errors import (
    ExceptionStatusMap,
    http_exception_for_exception,
)
from server.configurations.dependencies import get_training_service
from server.domain.jobs import JobCancelResponse, JobStartResponse, JobStatusResponse
from server.domain.training import (
    TrainingCheckpointListResponse,
    ResumeConfig,
    TrainingCheckpointDeleteResponse,
    TrainingCheckpointMetadataResponse,
    TrainingConfig,
    TrainingStatusResponse,
    TrainingStopResponse,
)
from server.services.training import TrainingService


router = APIRouter(prefix="/training", tags=["training"])

TRAINING_BAD_REQUEST_STATUS: ExceptionStatusMap = (
    (ValueError, status.HTTP_400_BAD_REQUEST),
)

###############################################################################
def _to_bad_request(exc: Exception) -> HTTPException:
    return http_exception_for_exception(
        exc,
        TRAINING_BAD_REQUEST_STATUS,
        default_detail=str(exc),
    )


###############################################################################
@router.post(
    "/start",
    response_model=JobStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_training(
    config: TrainingConfig,
    service: TrainingService = Depends(get_training_service),
) -> JobStartResponse:
    try:
        return JobStartResponse.model_validate(service.start_training(config))
    except FileExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise _to_bad_request(exc) from exc


###############################################################################
@router.post(
    "/resume",
    response_model=JobStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def resume_training(
    config: ResumeConfig,
    service: TrainingService = Depends(get_training_service),
) -> JobStartResponse:
    try:
        return JobStartResponse.model_validate(service.resume_training(config))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise _to_bad_request(exc) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


###############################################################################
@router.get(
    "/status",
    response_model=TrainingStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_status(
    service: TrainingService = Depends(get_training_service),
) -> TrainingStatusResponse:
    return TrainingStatusResponse.model_validate(service.get_status())


###############################################################################
@router.post(
    "/stop",
    response_model=TrainingStopResponse,
    status_code=status.HTTP_200_OK,
)
def stop_training(
    service: TrainingService = Depends(get_training_service),
) -> TrainingStopResponse:
    try:
        return TrainingStopResponse.model_validate(service.stop())
    except ValueError as exc:
        raise _to_bad_request(exc) from exc


###############################################################################
@router.get(
    "/checkpoints",
    response_model=TrainingCheckpointListResponse,
    status_code=status.HTTP_200_OK,
)
def get_checkpoints(
    service: TrainingService = Depends(get_training_service),
) -> TrainingCheckpointListResponse:
    return TrainingCheckpointListResponse(service.list_checkpoints())


###############################################################################
@router.get(
    "/checkpoints/{checkpoint}/metadata",
    response_model=TrainingCheckpointMetadataResponse,
    status_code=status.HTTP_200_OK,
)
def get_checkpoint_metadata(
    checkpoint: str,
    service: TrainingService = Depends(get_training_service),
) -> TrainingCheckpointMetadataResponse:
    try:
        return TrainingCheckpointMetadataResponse.model_validate(
            service.get_checkpoint_metadata(checkpoint)
        )
    except ValueError as exc:
        raise _to_bad_request(exc) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


###############################################################################
@router.delete(
    "/checkpoints/{checkpoint}",
    response_model=TrainingCheckpointDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_checkpoint(
    checkpoint: str,
    service: TrainingService = Depends(get_training_service),
) -> TrainingCheckpointDeleteResponse:
    try:
        return TrainingCheckpointDeleteResponse.model_validate(
            service.delete_checkpoint(checkpoint)
        )
    except ValueError as exc:
        raise _to_bad_request(exc) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


###############################################################################
@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_training_job_status(
    job_id: str,
    service: TrainingService = Depends(get_training_service),
) -> JobStatusResponse:
    try:
        return JobStatusResponse.model_validate(service.get_job(job_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


###############################################################################
@router.delete(
    "/jobs/{job_id}",
    response_model=JobCancelResponse,
    status_code=status.HTTP_200_OK,
)
def cancel_training_job(
    job_id: str,
    service: TrainingService = Depends(get_training_service),
) -> JobCancelResponse:
    try:
        return JobCancelResponse.model_validate(service.delete_job(job_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
