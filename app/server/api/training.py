from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from server.common.api_errors import ExceptionStatusMap, http_exception_for_exception
from server.configurations.dependencies import get_training_service
from server.contracts.jobs import JobCancelResponse, JobStartResponse, JobStatusResponse
from server.contracts.training import (
    TrainingCheckpointListResponse,
    ResumeConfig,
    TrainingCheckpointDeleteResponse,
    TrainingCheckpointMetadataResponse,
    TrainingConfig,
    TrainingStatusResponse,
    TrainingStopResponse,
)
router = APIRouter(prefix="/training", tags=["training"])

TRAINING_EXCEPTION_STATUS: ExceptionStatusMap = (
    (FileExistsError, status.HTTP_409_CONFLICT),
    (RuntimeError, status.HTTP_409_CONFLICT),
    (FileNotFoundError, status.HTTP_404_NOT_FOUND),
    (KeyError, status.HTTP_404_NOT_FOUND),
    (ValueError, status.HTTP_400_BAD_REQUEST),
)


###############################################################################
def _map_training_exception(exc: Exception) -> HTTPException:
    return http_exception_for_exception(
        exc,
        TRAINING_EXCEPTION_STATUS,
        default_detail="Unable to process training request.",
    )


###############################################################################
@router.post(
    "/start",
    response_model=JobStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_training(
    config: TrainingConfig,
    service: Any = Depends(get_training_service),
) -> JobStartResponse:
    try:
        return JobStartResponse.model_validate(service.start_training(config))
    except Exception as exc:
        raise _map_training_exception(exc) from exc


###############################################################################
@router.post(
    "/resume",
    response_model=JobStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def resume_training(
    config: ResumeConfig,
    service: Any = Depends(get_training_service),
) -> JobStartResponse:
    try:
        return JobStartResponse.model_validate(service.resume_training(config))
    except Exception as exc:
        raise _map_training_exception(exc) from exc


###############################################################################
@router.get(
    "/status",
    response_model=TrainingStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_status(
    service: Any = Depends(get_training_service),
) -> TrainingStatusResponse:
    return TrainingStatusResponse.model_validate(service.get_status())


###############################################################################
@router.post(
    "/stop",
    response_model=TrainingStopResponse,
    status_code=status.HTTP_200_OK,
)
def stop_training(
    service: Any = Depends(get_training_service),
) -> TrainingStopResponse:
    try:
        return TrainingStopResponse.model_validate(service.stop())
    except Exception as exc:
        raise _map_training_exception(exc) from exc


###############################################################################
@router.get(
    "/checkpoints",
    response_model=TrainingCheckpointListResponse,
    status_code=status.HTTP_200_OK,
)
def get_checkpoints(
    service: Any = Depends(get_training_service),
) -> TrainingCheckpointListResponse:
    return TrainingCheckpointListResponse.model_validate(service.list_checkpoints())


###############################################################################
@router.get(
    "/checkpoints/{checkpoint}/metadata",
    response_model=TrainingCheckpointMetadataResponse,
    status_code=status.HTTP_200_OK,
)
def get_checkpoint_metadata(
    checkpoint: str,
    service: Any = Depends(get_training_service),
) -> TrainingCheckpointMetadataResponse:
    try:
        return TrainingCheckpointMetadataResponse.model_validate(
            service.get_checkpoint_metadata(checkpoint)
        )
    except Exception as exc:
        raise _map_training_exception(exc) from exc


###############################################################################
@router.delete(
    "/checkpoints/{checkpoint}",
    response_model=TrainingCheckpointDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_checkpoint(
    checkpoint: str,
    service: Any = Depends(get_training_service),
) -> TrainingCheckpointDeleteResponse:
    try:
        return TrainingCheckpointDeleteResponse.model_validate(
            service.delete_checkpoint(checkpoint)
        )
    except Exception as exc:
        raise _map_training_exception(exc) from exc


###############################################################################
@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_training_job_status(
    job_id: str,
    service: Any = Depends(get_training_service),
) -> JobStatusResponse:
    try:
        return JobStatusResponse.model_validate(service.get_job(job_id))
    except Exception as exc:
        raise _map_training_exception(exc) from exc


###############################################################################
@router.delete(
    "/jobs/{job_id}",
    response_model=JobCancelResponse,
    status_code=status.HTTP_200_OK,
)
def cancel_training_job(
    job_id: str,
    service: Any = Depends(get_training_service),
) -> JobCancelResponse:
    try:
        return JobCancelResponse.model_validate(service.delete_job(job_id))
    except Exception as exc:
        raise _map_training_exception(exc) from exc
