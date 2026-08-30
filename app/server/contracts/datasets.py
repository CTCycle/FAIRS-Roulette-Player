from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


###############################################################################
class DatasetRecord(BaseModel):
    dataset_id: int
    dataset_name: str
    dataset_kind: str
    created_at: datetime | str | None = None


###############################################################################
class DatasetSummaryRecord(BaseModel):
    dataset_id: int
    dataset_name: str
    dataset_kind: str
    created_at: datetime | str | None = None
    row_count: int


###############################################################################
class DatasetListResponse(BaseModel):
    datasets: list[DatasetRecord]


###############################################################################
class DatasetSummaryResponse(BaseModel):
    datasets: list[DatasetSummaryRecord]


###############################################################################
class DatasetDeleteResponse(BaseModel):
    status: str
    dataset_id: int
