from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from starlette.concurrency import run_in_threadpool

from server.common.api_errors import ExceptionStatusMap, http_exception_for_exception
from server.configurations.dependencies import get_dataset_service
from server.contracts.upload import DatasetKind, UploadRequest, UploadResponse
router = APIRouter(prefix="/data", tags=["data"])
UPLOAD_EXCEPTION_STATUS: ExceptionStatusMap = (
    (ValueError, status.HTTP_400_BAD_REQUEST),
)


###############################################################################
@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload(
    file: UploadFile = File(...),
    dataset_kind: DatasetKind = Query(...),
    csv_separator: str = Query(";", min_length=1, max_length=1),
    sheet_name: str | int = Query(0),
    service: Any = Depends(get_dataset_service),
) -> UploadResponse:
    request = UploadRequest(
        dataset_kind=dataset_kind,
        csv_separator=csv_separator,
        sheet_name=sheet_name,
    )
    try:
        try:
            content = await file.read()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to read uploaded file.",
            ) from exc

        try:
            return await run_in_threadpool(
                service.import_upload,
                content,
                file.filename,
                request,
            )
        except ValueError as exc:
            message = str(exc)
            if "too large" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=message,
                ) from exc
            raise http_exception_for_exception(
                exc,
                UPLOAD_EXCEPTION_STATUS,
                default_detail=message,
            ) from exc
    finally:
        await file.close()
