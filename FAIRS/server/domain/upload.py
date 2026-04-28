from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

DatasetTable = Literal["roulette_series", "inference_context"]


###############################################################################
class UploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table: DatasetTable
    csv_separator: str = ";"
    sheet_name: str | int = 0


###############################################################################
class UploadResponse(BaseModel):
    table: DatasetTable
    filename: str
    rows_imported: int
    dataset_id: int | None
    dataset_name: str | None
    dataset_kind: str | None
    columns: list[str]
