from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from FAIRS.server.common.utils.logger import logger
from FAIRS.server.services.importer import DatasetImportService, DatasetTable
from FAIRS.server.services.loader import TabularFileLoader


router = APIRouter(prefix="/data", tags=["data"])
ALLOWED_CSV_SEPARATORS = {",", ";", "\t", "|"}
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
MAX_FILENAME_LENGTH = 255
MAX_EXCEL_SHEET_NAME_LENGTH = 128


###############################################################################
def normalize_filename(filename: str | None) -> str:
    if filename is None:
        raise ValueError("Missing filename.")
    cleaned = os.path.basename(filename).strip()
    if not cleaned:
        raise ValueError("Missing filename.")
    if len(cleaned) > MAX_FILENAME_LENGTH:
        raise ValueError("Filename is too long.")
    if any(ord(char) < 32 for char in cleaned):
        raise ValueError("Filename contains invalid control characters.")
    return cleaned


# -----------------------------------------------------------------------------
def normalize_csv_separator(separator: str) -> str:
    cleaned = separator.strip()
    if cleaned not in ALLOWED_CSV_SEPARATORS:
        supported = ", ".join(sorted(repr(value) for value in ALLOWED_CSV_SEPARATORS))
        raise ValueError(f"Unsupported csv_separator. Allowed values: {supported}.")
    return cleaned


# -----------------------------------------------------------------------------
def normalize_sheet_name(sheet_name: str | int) -> str | int:
    if isinstance(sheet_name, bool):
        raise ValueError("sheet_name must be an integer index or a string.")
    if isinstance(sheet_name, int):
        if sheet_name < 0 or sheet_name > 255:
            raise ValueError("sheet_name index must be between 0 and 255.")
        return sheet_name
    cleaned = sheet_name.strip()
    if not cleaned:
        raise ValueError("sheet_name cannot be empty.")
    if len(cleaned) > MAX_EXCEL_SHEET_NAME_LENGTH:
        raise ValueError("sheet_name is too long.")
    if any(ord(char) < 32 for char in cleaned):
        raise ValueError("sheet_name contains invalid control characters.")
    return cleaned


###############################################################################
class DataUploadEndpoint:
    def __init__(self, router: APIRouter) -> None:
        self.router = router
        self.loader = TabularFileLoader()
        self.importer = DatasetImportService()

    # -------------------------------------------------------------------------
    async def upload(
        self,
        file: UploadFile = File(...),
        table: DatasetTable = Query(...),
        csv_separator: str = Query(";", min_length=1, max_length=1),
        sheet_name: str | int = Query(0),
    ) -> dict[str, Any]:
        try:
            filename = normalize_filename(file.filename)
            csv_separator = normalize_csv_separator(csv_separator)
            sheet_name = normalize_sheet_name(sheet_name)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        dataset_name = None
        if table in ["roulette_series", "inference_context"]:
            base_name = os.path.splitext(filename)[0].strip()
            dataset_name = base_name if base_name else "dataset"

        try:
            content = await file.read()
        except Exception as exc:
            logger.exception("Failed to read uploaded file.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to read uploaded file.",
            ) from exc

        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    "Uploaded file is too large. "
                    f"Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."
                ),
            )

        try:
            dataframe = self.loader.load_bytes(
                content,
                filename,
                csv_separator=csv_separator,
                sheet_name=sheet_name,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("Failed to parse uploaded file.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to parse uploaded file.",
            ) from exc

        try:
            imported = self.importer.import_dataframe(
                dataframe,
                table,
                dataset_name=dataset_name,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("Failed to import dataset into the database.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to import dataset into the database.",
            ) from exc

        return {
            "table": table,
            "filename": filename,
            "rows_imported": imported.get("rows_imported", 0),
            "dataset_id": imported.get("dataset_id"),
            "dataset_name": imported.get("dataset_name"),
            "dataset_kind": imported.get("dataset_kind"),
            "columns": list(dataframe.columns),
        }

    # -------------------------------------------------------------------------
    def add_routes(self) -> None:
        self.router.add_api_route(
            "/upload",
            self.upload,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )


upload_endpoint = DataUploadEndpoint(router=router)
upload_endpoint.add_routes()
