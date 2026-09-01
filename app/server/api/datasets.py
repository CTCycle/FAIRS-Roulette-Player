from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path, status

from server.common.api_errors import ExceptionStatusMap, http_exception_for_exception
from server.common.exceptions import CheckpointReferenceError
from server.configurations.dependencies import get_dataset_service
from server.contracts.datasets import (
    DatasetDeleteResponse,
    DatasetListResponse,
    DatasetSummaryResponse,
)
router = APIRouter(prefix="/datasets", tags=["datasets"])
DATASET_EXCEPTION_STATUS: ExceptionStatusMap = (
    (CheckpointReferenceError, status.HTTP_409_CONFLICT),
    (ValueError, status.HTTP_400_BAD_REQUEST),
)


###############################################################################
@router.get(
    "/training",
    response_model=DatasetListResponse,
    status_code=status.HTTP_200_OK,
)
def list_roulette_datasets(
    service: Any = Depends(get_dataset_service),
) -> DatasetListResponse:
    return service.list_training_datasets()


###############################################################################
@router.get(
    "/training/summary",
    response_model=DatasetSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def list_roulette_datasets_summary(
    service: Any = Depends(get_dataset_service),
) -> DatasetSummaryResponse:
    return service.list_training_dataset_summaries()


###############################################################################
@router.delete(
    "/training/{dataset_id}",
    response_model=DatasetDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_roulette_dataset(
    dataset_id: int = Path(..., ge=1),
    service: Any = Depends(get_dataset_service),
) -> DatasetDeleteResponse:
    try:
        return service.delete_training_dataset(dataset_id)
    except (CheckpointReferenceError, ValueError) as exc:
        raise http_exception_for_exception(
            exc,
            DATASET_EXCEPTION_STATUS,
            default_detail="Unable to delete dataset.",
        ) from exc
