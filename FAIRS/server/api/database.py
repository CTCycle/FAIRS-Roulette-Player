from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from FAIRS.server.configurations.dependencies import get_data_serializer
from FAIRS.server.domain.database import (
    DatasetDeleteResponse,
    DatasetListResponse,
    DatasetSummaryResponse,
)
from FAIRS.server.services.datasets import DatasetService
from FAIRS.server.services.importer import DatasetImportService
from FAIRS.server.services.loader import TabularFileLoader


router = APIRouter(prefix="/database", tags=["database"])


###############################################################################
def build_dataset_service(serializer: object) -> DatasetService:
    return DatasetService(
        serializer=serializer,
        importer=DatasetImportService(serializer=serializer),
        loader=TabularFileLoader(),
    )


###############################################################################
@router.get(
    "/roulette-series/datasets",
    response_model=DatasetListResponse,
    status_code=status.HTTP_200_OK,
)
def list_roulette_datasets(
    serializer: object = Depends(get_data_serializer),
) -> DatasetListResponse:
    service = build_dataset_service(serializer)
    return service.list_training_datasets()


###############################################################################
@router.get(
    "/roulette-series/datasets/summary",
    response_model=DatasetSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def list_roulette_datasets_summary(
    serializer: object = Depends(get_data_serializer),
) -> DatasetSummaryResponse:
    service = build_dataset_service(serializer)
    return service.list_training_dataset_summaries()


###############################################################################
@router.delete(
    "/roulette-series/datasets/{dataset_id}",
    response_model=DatasetDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_roulette_dataset(
    dataset_id: int = Path(..., ge=1),
    serializer: object = Depends(get_data_serializer),
) -> DatasetDeleteResponse:
    service = build_dataset_service(serializer)
    try:
        return service.delete_training_dataset(dataset_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
