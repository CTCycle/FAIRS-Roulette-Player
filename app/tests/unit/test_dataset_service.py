from __future__ import annotations

from unittest.mock import Mock

import pandas as pd
import pytest

from server.domain.upload import UploadRequest
from server.services.datasets import DatasetService


def build_dataset_service() -> tuple[DatasetService, Mock, Mock, Mock]:
    serializer = Mock()
    importer = Mock()
    loader = Mock()
    service = DatasetService(serializer=serializer, importer=importer, loader=loader)
    return service, serializer, importer, loader


def test_import_upload_normalizes_filename_separator_and_sheet_name() -> None:
    service, _, importer, loader = build_dataset_service()
    loader.load_bytes.return_value = pd.DataFrame({"idx": [0], "outcome": [1]})
    importer.import_dataframe.return_value = {
        "rows_imported": 1,
        "dataset_id": 10,
        "dataset_name": "sample",
        "dataset_kind": "training",
    }

    response = service.import_upload(
        content=b"idx,outcome\n0,1\n",
        filename=r"..\sample.csv",
        request=UploadRequest(table="roulette_series", csv_separator=",", sheet_name=0),
    )

    assert response.filename == "sample.csv"
    assert response.rows_imported == 1
    loader.load_bytes.assert_called_once()
    importer.import_dataframe.assert_called_once()


def test_import_upload_rejects_oversized_payload() -> None:
    service, _, _, _ = build_dataset_service()
    with pytest.raises(ValueError, match="too large"):
        service.import_upload(
            content=b"x" * (25 * 1024 * 1024 + 1),
            filename="big.csv",
            request=UploadRequest(table="roulette_series"),
        )


def test_dataset_list_and_delete_delegate_to_serializer() -> None:
    service, serializer, _, _ = build_dataset_service()
    serializer.list_datasets.return_value = [
        {"dataset_id": 1, "dataset_name": "a", "dataset_kind": "training", "created_at": None}
    ]
    serializer.list_datasets_summary.return_value = [
        {
            "dataset_id": 1,
            "dataset_name": "a",
            "dataset_kind": "training",
            "created_at": None,
            "row_count": 5,
        }
    ]

    list_response = service.list_training_datasets()
    summary_response = service.list_training_dataset_summaries()
    delete_response = service.delete_training_dataset(1)

    assert len(list_response.datasets) == 1
    assert len(summary_response.datasets) == 1
    assert delete_response.status == "deleted"
    serializer.delete_dataset.assert_called_once_with(1)
