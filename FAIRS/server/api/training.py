from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from FAIRS.server.configurations.dependencies import get_training_service
from FAIRS.server.domain.jobs import JobCancelResponse, JobStartResponse, JobStatusResponse
from FAIRS.server.domain.training import (
    ResumeConfig,
    TrainingCheckpointDeleteResponse,
    TrainingCheckpointMetadataResponse,
    TrainingConfig,
    TrainingStatusResponse,
    TrainingStopResponse,
)
from FAIRS.server.services.training import TrainingService


router = APIRouter(prefix="/training", tags=["training"])


###############################################################################
def _to_bad_request(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
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
) -> dict[str, Any]:
    try:
        return service.start_training(config)
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
) -> dict[str, Any]:
    try:
        return service.resume_training(config)
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
def get_status(service: TrainingService = Depends(get_training_service)) -> dict[str, Any]:
    return service.get_status()


###############################################################################
@router.post(
    "/stop",
    response_model=TrainingStopResponse,
    status_code=status.HTTP_200_OK,
)
def stop_training(
    service: TrainingService = Depends(get_training_service),
) -> dict[str, Any]:
    try:
        return service.stop()
    except ValueError as exc:
        raise _to_bad_request(exc) from exc


###############################################################################
@router.get(
    "/checkpoints",
    status_code=status.HTTP_200_OK,
)
def get_checkpoints(
    service: TrainingService = Depends(get_training_service),
) -> list[str]:
    return service.checkpoint_service.list_checkpoints()


###############################################################################
@router.get(
    "/checkpoints/{checkpoint}/metadata",
    response_model=TrainingCheckpointMetadataResponse,
    status_code=status.HTTP_200_OK,
)
def get_checkpoint_metadata(
    checkpoint: str,
    service: TrainingService = Depends(get_training_service),
) -> dict[str, Any]:
    try:
        return service.checkpoint_service.get_metadata(checkpoint)
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
) -> dict[str, str]:
    try:
        service.checkpoint_service.delete_checkpoint(checkpoint)
        return {"status": "success", "message": f"Checkpoint {checkpoint} deleted"}
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
) -> dict[str, Any]:
    try:
        return service.get_job(job_id)
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
) -> dict[str, Any]:
    try:
        return service.delete_job(job_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
