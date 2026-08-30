from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

DatasetKind = Literal["training", "inference"]


###############################################################################
class UploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_kind: DatasetKind
    csv_separator: str = ";"
    sheet_name: str | int = 0


###############################################################################
class UploadResponse(BaseModel):
    filename: str
    rows_imported: int
    dataset_id: int | None
    dataset_name: str | None
    dataset_kind: str | None
    columns: list[str]
