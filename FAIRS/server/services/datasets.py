from __future__ import annotations

import os

from FAIRS.server.domain.database import (
    DatasetDeleteResponse,
    DatasetListResponse,
    DatasetSummaryResponse,
)
from FAIRS.server.domain.upload import UploadRequest, UploadResponse
from FAIRS.server.repositories.serialization.data import DataSerializer
from FAIRS.server.services.importer import DatasetImportService
from FAIRS.server.services.loader import TabularFileLoader

ALLOWED_CSV_SEPARATORS = {",", ";", "\t", "|"}
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
MAX_FILENAME_LENGTH = 255
MAX_EXCEL_SHEET_NAME_LENGTH = 128


###############################################################################
def normalize_filename(filename: str | None) -> str:
    if filename is None:
        raise ValueError("Missing filename.")
    # Normalize both Unix and Windows separators before taking basename.
    cleaned = os.path.basename(filename.replace("\\", "/")).strip()
    if not cleaned:
        raise ValueError("Missing filename.")
    if len(cleaned) > MAX_FILENAME_LENGTH:
        raise ValueError("Filename is too long.")
    if any(ord(char) < 32 for char in cleaned):
        raise ValueError("Filename contains invalid control characters.")
    return cleaned


###############################################################################
def normalize_csv_separator(separator: str) -> str:
    cleaned = separator.strip()
    if cleaned not in ALLOWED_CSV_SEPARATORS:
        supported = ", ".join(sorted(repr(value) for value in ALLOWED_CSV_SEPARATORS))
        raise ValueError(f"Unsupported csv_separator. Allowed values: {supported}.")
    return cleaned


###############################################################################
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
class DatasetService:
    def __init__(
        self,
        serializer: DataSerializer,
        importer: DatasetImportService,
        loader: TabularFileLoader,
    ) -> None:
        self.serializer = serializer
        self.importer = importer
        self.loader = loader

    # -------------------------------------------------------------------------
    def import_upload(
        self,
        content: bytes,
        filename: str | None,
        request: UploadRequest,
    ) -> UploadResponse:
        normalized_filename = normalize_filename(filename)
        csv_separator = normalize_csv_separator(request.csv_separator)
        sheet_name = normalize_sheet_name(request.sheet_name)

        if not content:
            raise ValueError("Uploaded file is empty.")
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError(
                "Uploaded file is too large. "
                f"Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."
            )

        dataframe = self.loader.load_bytes(
            content,
            normalized_filename,
            csv_separator=csv_separator,
            sheet_name=sheet_name,
        )

        dataset_name = None
        if request.table in {"roulette_series", "inference_context"}:
            base_name = os.path.splitext(normalized_filename)[0].strip()
            dataset_name = base_name if base_name else "dataset"

        imported = self.importer.import_dataframe(
            dataframe,
            request.table,
            dataset_name=dataset_name,
        )
        return UploadResponse(
            table=request.table,
            filename=normalized_filename,
            rows_imported=int(imported.get("rows_imported", 0)),
            dataset_id=imported.get("dataset_id"),
            dataset_name=imported.get("dataset_name"),
            dataset_kind=imported.get("dataset_kind"),
            columns=[str(column) for column in dataframe.columns],
        )

    # -------------------------------------------------------------------------
    def list_training_datasets(self) -> DatasetListResponse:
        datasets = self.serializer.list_datasets(dataset_kind="training")
        return DatasetListResponse(datasets=datasets)

    # -------------------------------------------------------------------------
    def list_training_dataset_summaries(self) -> DatasetSummaryResponse:
        datasets = self.serializer.list_datasets_summary(dataset_kind="training")
        return DatasetSummaryResponse(datasets=datasets)

    # -------------------------------------------------------------------------
    def delete_training_dataset(self, dataset_id: int) -> DatasetDeleteResponse:
        self.serializer.delete_dataset(dataset_id)
        return DatasetDeleteResponse(status="deleted", dataset_id=dataset_id)
