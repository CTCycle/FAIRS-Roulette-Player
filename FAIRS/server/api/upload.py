from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from FAIRS.server.configurations.dependencies import get_data_serializer
from FAIRS.server.domain.upload import DatasetTable, UploadRequest, UploadResponse
from FAIRS.server.services.datasets import DatasetService
from FAIRS.server.services.importer import DatasetImportService
from FAIRS.server.services.loader import TabularFileLoader


router = APIRouter(prefix="/data", tags=["data"])


###############################################################################
def build_dataset_service(serializer: object) -> DatasetService:
    return DatasetService(
        serializer=serializer,
        importer=DatasetImportService(serializer=serializer),
        loader=TabularFileLoader(),
    )


###############################################################################
@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload(
    file: UploadFile = File(...),
    table: DatasetTable = Query(...),
    csv_separator: str = Query(";", min_length=1, max_length=1),
    sheet_name: str | int = Query(0),
    serializer: object = Depends(get_data_serializer),
) -> UploadResponse:
    service = build_dataset_service(serializer)
    request = UploadRequest(
        table=table,
        csv_separator=csv_separator,
        sheet_name=sheet_name,
    )
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read uploaded file.",
        ) from exc

    try:
        return service.import_upload(content, file.filename, request)
    except ValueError as exc:
        message = str(exc)
        if "too large" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc
