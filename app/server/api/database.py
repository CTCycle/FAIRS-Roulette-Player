from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from server.configurations.dependencies import get_dataset_service
from server.domain.database import (
    DatasetDeleteResponse,
    DatasetListResponse,
    DatasetSummaryResponse,
)
from server.services.datasets import DatasetService


router = APIRouter(prefix="/database", tags=["database"])


###############################################################################
@router.get(
    "/roulette-series/datasets",
    response_model=DatasetListResponse,
    status_code=status.HTTP_200_OK,
)
def list_roulette_datasets(
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetListResponse:
    return service.list_training_datasets()


###############################################################################
@router.get(
    "/roulette-series/datasets/summary",
    response_model=DatasetSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def list_roulette_datasets_summary(
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetSummaryResponse:
    return service.list_training_dataset_summaries()


###############################################################################
@router.delete(
    "/roulette-series/datasets/{dataset_id}",
    response_model=DatasetDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_roulette_dataset(
    dataset_id: int = Path(..., ge=1),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetDeleteResponse:
    try:
        return service.delete_training_dataset(dataset_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
