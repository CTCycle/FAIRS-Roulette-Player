from __future__ import annotations

from pathlib import PurePath

from server.contracts.datasets import (
    DatasetDeleteResponse,
    DatasetListResponse,
    DatasetSummaryResponse,
)
from server.contracts.upload import UploadRequest, UploadResponse
from server.common.exceptions import CheckpointReferenceError
from server.repositories.datasets import DatasetRepository
from server.services.checkpoints import CheckpointService
from server.services.importer import DatasetImportService
from server.services.loader import TabularFileLoader

ALLOWED_CSV_SEPARATORS = {",", ";", "\t", "|"}
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
MAX_FILENAME_LENGTH = 255
MAX_EXCEL_SHEET_NAME_LENGTH = 128


###############################################################################
def normalize_filename(filename: str | None) -> str:
    if filename is None:
        raise ValueError("Missing filename.")
    # Normalize both Unix and Windows separators before taking basename.
    cleaned = PurePath(filename.replace("\\", "/")).name.strip()
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
    # -------------------------------------------------------------------------
    def __init__(
        self,
        dataset_repository: DatasetRepository,
        importer: DatasetImportService,
        loader: TabularFileLoader,
        checkpoint_service: CheckpointService | None = None,
    ) -> None:
        self.dataset_repository = dataset_repository
        self.importer = importer
        self.loader = loader
        self.checkpoint_service = checkpoint_service

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

        base_name = PurePath(normalized_filename).stem.strip()
        dataset_name = base_name if base_name else "dataset"

        imported = self.importer.import_dataframe(
            dataframe,
            request.dataset_kind,
            dataset_name=dataset_name,
        )
        return UploadResponse(
            filename=normalized_filename,
            rows_imported=int(imported.get("rows_imported", 0)),
            dataset_id=imported.get("dataset_id"),
            dataset_name=imported.get("dataset_name"),
            dataset_kind=imported.get("dataset_kind"),
            columns=[str(column) for column in dataframe.columns],
        )

    # -------------------------------------------------------------------------
    def list_training_datasets(self) -> DatasetListResponse:
        datasets = self.dataset_repository.list(dataset_kind="training")
        return DatasetListResponse(datasets=datasets)

    # -------------------------------------------------------------------------
    def list_training_dataset_summaries(self) -> DatasetSummaryResponse:
        datasets = self.dataset_repository.summaries(dataset_kind="training")
        return DatasetSummaryResponse(datasets=datasets)

    # -------------------------------------------------------------------------
    def delete_training_dataset(self, dataset_id: int) -> DatasetDeleteResponse:
        if self.checkpoint_service is not None:
            references = self.checkpoint_service.find_dataset_references(dataset_id)
            if references:
                joined = ", ".join(references)
                raise CheckpointReferenceError(
                    f"Dataset '{dataset_id}' is referenced by checkpoint(s): {joined}. "
                    "Delete those checkpoints before deleting the dataset."
                )
        self.dataset_repository.delete(dataset_id)
        return DatasetDeleteResponse(status="deleted", dataset_id=dataset_id)
