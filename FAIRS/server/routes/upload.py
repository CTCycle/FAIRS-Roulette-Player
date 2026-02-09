from __future__ import annotations

from collections.abc import Callable
import os
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from FAIRS.server.common.utils.logger import logger
from FAIRS.server.services.importer import DatasetImportService, DatasetTable
from FAIRS.server.services.loader import TabularFileLoader


router = APIRouter(prefix="/data", tags=["data"])


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
        csv_separator: str = Query(";"),
        sheet_name: str | int | None = Query(0),
    ) -> dict[str, Any]:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing filename.",
            )
        name = None
        if table in ["roulette_series", "inference_context"]:
            base_name = os.path.splitext(os.path.basename(file.filename))[0].strip()
            name = base_name if base_name else "dataset"

        try:
            content = await file.read()
        except Exception as exc:
            logger.exception("Failed to read uploaded file.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to read uploaded file.",
            ) from exc

        try:
            dataframe = self.loader.load_bytes(
                content,
                file.filename,
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
                dataframe, table, name=name
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
            "filename": file.filename,
            "rows_imported": imported,
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
