"""
E2E tests for Data Upload API endpoint.
Tests: POST /data/upload
"""

from io import BytesIO
from uuid import uuid4

from openpyxl import Workbook
from playwright.sync_api import APIRequestContext

from server.services.datasets import MAX_UPLOAD_SIZE_BYTES

###############################################################################
def load_dataset_summary_entry(
    api_context: APIRequestContext, dataset_id: int
) -> dict | None:
    response = api_context.get("/api/datasets/training/summary")
    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    datasets = response.json().get("datasets", [])
    return next(
        (item for item in datasets if item.get("dataset_id") == dataset_id),
        None,
    )

###############################################################################
def delete_uploaded_dataset(
    api_context: APIRequestContext, dataset_id: int
) -> None:
    response = api_context.delete(f"/api/datasets/training/{dataset_id}")
    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    assert load_dataset_summary_entry(api_context, dataset_id) is None

###############################################################################
class TestDataUploadEndpoint:
    """Tests for the /data/upload API endpoint."""

    # -------------------------------------------------------------------------
    def test_upload_without_file_returns_422(self, api_context: APIRequestContext):
        """POST /data/upload without a file should return 422 (validation error)."""
        response = api_context.post("/api/data/upload?dataset_kind=training")
        # FastAPI returns 422 for missing required fields
        assert response.status == 422

    # -------------------------------------------------------------------------
    def test_upload_with_invalid_dataset_kind_returns_422(
        self, api_context: APIRequestContext
    ):
        """POST /data/upload with an invalid dataset kind should return 422."""
        # Create a minimal CSV in memory
        csv_content = b"extraction\n1\n2\n3"

        response = api_context.post(
            "/api/data/upload?dataset_kind=INVALID_DATASET_KIND",
            multipart={
                "file": {
                    "name": "test.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content,
                }
            },
        )
        # Invalid dataset kind enum value should fail validation
        assert response.status == 422

    # -------------------------------------------------------------------------
    def test_upload_valid_csv_to_training_dataset(self, api_context: APIRequestContext):
        """POST /data/upload with valid CSV should import data successfully."""
        dataset_name = f"val06_csv_{uuid4().hex[:8]}"
        csv_content = b"draw_index,observed_outcome\n0,0\n1,15\n2,32\n3,7\n4,21"
        dataset_id = None
        try:
            response = api_context.post(
                "/api/data/upload?dataset_kind=training&csv_separator=%2C",
                multipart={
                    "file": {
                        "name": f"{dataset_name}.csv",
                        "mimeType": "text/csv",
                        "buffer": csv_content,
                    }
                },
            )

            assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
            data = response.json()
            dataset_id = data.get("dataset_id")
            assert isinstance(dataset_id, int)
            assert data["filename"] == f"{dataset_name}.csv"
            assert data["dataset_name"] == dataset_name
            assert data["dataset_kind"] == "training"
            assert data["rows_imported"] == 5
            assert data["columns"] == ["draw_index", "observed_outcome"]
        finally:
            if isinstance(dataset_id, int):
                delete_uploaded_dataset(api_context, dataset_id)

    # -------------------------------------------------------------------------
    def test_upload_empty_file_returns_400(self, api_context: APIRequestContext):
        """POST /data/upload with empty content should return 400."""
        response = api_context.post(
            "/api/data/upload?dataset_kind=training",
            multipart={
                "file": {
                    "name": "empty.csv",
                    "mimeType": "text/csv",
                    "buffer": b"",
                }
            },
        )
        # Empty file should fail parsing
        assert response.status == 400

###############################################################################
class TestDataUploadEdgeCases:
    """Edge case tests for data upload functionality."""

    # -------------------------------------------------------------------------
    def test_upload_unsupported_extension_returns_400(
        self, api_context: APIRequestContext
    ):
        response = api_context.post(
            "/api/data/upload?dataset_kind=training",
            multipart={
                "file": {
                    "name": "val06_unsupported.txt",
                    "mimeType": "text/plain",
                    "buffer": b"index,outcome\n0,1\n1,2",
                }
            },
        )
        assert response.status == 400
        assert "detail" in response.json()

    # -------------------------------------------------------------------------
    def test_upload_training_file_with_one_column_returns_400(
        self, api_context: APIRequestContext
    ):
        response = api_context.post(
            "/api/data/upload?dataset_kind=training",
            multipart={
                "file": {
                    "name": "val06_one_column.csv",
                    "mimeType": "text/csv",
                    "buffer": b"outcome\n1\n2\n3",
                }
            },
        )
        assert response.status == 400
        assert "two columns" in response.json()["detail"]

    # -------------------------------------------------------------------------
    def test_upload_with_no_valid_rows_returns_400(
        self, api_context: APIRequestContext
    ):
        response = api_context.post(
            "/api/data/upload?dataset_kind=training&csv_separator=%2C",
            multipart={
                "file": {
                    "name": "val06_no_valid_rows.csv",
                    "mimeType": "text/csv",
                    "buffer": b"index,outcome\n0,37\n1,-1\n2,not-an-integer",
                }
            },
        )
        assert response.status == 400
        assert "No valid roulette" in response.json()["detail"]

    # -------------------------------------------------------------------------
    def test_upload_oversized_file_returns_413(
        self, api_context: APIRequestContext
    ):
        response = api_context.post(
            "/api/data/upload?dataset_kind=training",
            multipart={
                "file": {
                    "name": "val06_oversized.csv",
                    "mimeType": "text/csv",
                    "buffer": b"x" * (MAX_UPLOAD_SIZE_BYTES + 1),
                }
            },
        )
        assert response.status == 413
        assert "too large" in response.json()["detail"].lower()

    # -------------------------------------------------------------------------
    def test_upload_valid_xlsx_to_training_dataset(
        self, api_context: APIRequestContext
    ):
        """A real workbook imports through the public upload endpoint."""
        dataset_name = f"val06_xlsx_{uuid4().hex[:8]}"
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["draw_index", "observed_outcome"])
        worksheet.append([0, 0])
        worksheet.append([1, 15])
        worksheet.append([2, 32])
        worksheet.append([3, 36])
        buffer = BytesIO()
        workbook.save(buffer)
        dataset_id = None

        try:
            response = api_context.post(
                "/api/data/upload?dataset_kind=training&sheet_name=0",
                multipart={
                    "file": {
                        "name": f"{dataset_name}.xlsx",
                        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "buffer": buffer.getvalue(),
                    }
                },
            )
            assert response.ok, (
                f"Expected 200, got {response.status}: {response.text()}"
            )
            payload = response.json()
            dataset_id = payload.get("dataset_id")
            assert isinstance(dataset_id, int)
            assert payload["filename"] == f"{dataset_name}.xlsx"
            assert payload["dataset_name"] == dataset_name
            assert payload["dataset_kind"] == "training"
            assert payload["rows_imported"] == 4
            assert payload["columns"] == ["draw_index", "observed_outcome"]

            summary_entry = load_dataset_summary_entry(api_context, dataset_id)
            assert summary_entry is not None
            assert summary_entry["dataset_name"] == dataset_name
            assert summary_entry["row_count"] == 4
        finally:
            if isinstance(dataset_id, int):
                delete_uploaded_dataset(api_context, dataset_id)

    # -------------------------------------------------------------------------
    def test_upload_malformed_xlsx_returns_400(self, api_context: APIRequestContext):
        """Malformed XLSX bytes are rejected independently of valid imports."""
        response = api_context.post(
            "/api/data/upload?dataset_kind=training&sheet_name=0",
            multipart={
                "file": {
                    "name": "val06_malformed.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "buffer": b"not a real xlsx",
                }
            },
        )
        assert response.status == 400
        payload = response.json()
        assert "detail" in payload

    # -------------------------------------------------------------------------
    def test_upload_with_custom_separator(self, api_context: APIRequestContext):
        """POST /data/upload should respect csv_separator parameter."""
        dataset_name = f"val06_semicolon_{uuid4().hex[:8]}"
        # CSV with semicolon separator
        csv_content = b"index;value\n0;0\n1;32\n2;15"
        dataset_id = None
        try:
            response = api_context.post(
                "/api/data/upload?dataset_kind=training&csv_separator=%3B",
                multipart={
                    "file": {
                        "name": f"{dataset_name}.csv",
                        "mimeType": "text/csv",
                        "buffer": csv_content,
                    }
                },
            )
            assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
            data = response.json()
            dataset_id = data.get("dataset_id")
            assert data["dataset_name"] == dataset_name
            assert data["rows_imported"] == 3
            assert data["dataset_kind"] == "training"
            summary_entry = load_dataset_summary_entry(api_context, dataset_id)
            assert summary_entry is not None
            assert summary_entry["row_count"] == 3
        finally:
            if isinstance(dataset_id, int):
                delete_uploaded_dataset(api_context, dataset_id)

    # -------------------------------------------------------------------------
    def test_upload_filters_invalid_outcomes_and_enriches_all_valid_rows(
        self, api_context: APIRequestContext
    ):
        """POST /data/upload should discard invalid outcomes and enrich valid rows."""
        dataset_name = f"val06_normalize_{uuid4().hex[:8]}"
        csv_content = (
            b"spin,result\n10,5\n11,37\n12,-1\n13,0\n14,36\n15,abc\n16,7.2\n17,7\n"
        )
        dataset_id = None
        try:
            response = api_context.post(
                "/api/data/upload?dataset_kind=training&csv_separator=%2C",
                multipart={
                    "file": {
                        "name": f"{dataset_name}.csv",
                        "mimeType": "text/csv",
                        "buffer": csv_content,
                    }
                },
            )
            assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
            payload = response.json()
            dataset_id = payload.get("dataset_id")
            assert isinstance(dataset_id, int) and dataset_id > 0
            assert payload["rows_imported"] == 4
            summary_entry = load_dataset_summary_entry(api_context, dataset_id)
            assert summary_entry is not None
            assert summary_entry["row_count"] == 4
        finally:
            if isinstance(dataset_id, int):
                delete_uploaded_dataset(api_context, dataset_id)

    # -------------------------------------------------------------------------
    def test_same_logical_name_replaces_rows_and_preserves_dataset_id(
        self, api_context: APIRequestContext
    ):
        """Case-insensitive reimport replaces a dataset rather than appending."""
        dataset_name = f"val06_replace_{uuid4().hex[:8]}"
        dataset_id = None

        try:
            first_response = api_context.post(
                "/api/data/upload?dataset_kind=training&csv_separator=%2C",
                multipart={
                    "file": {
                        "name": f"{dataset_name}.csv",
                        "mimeType": "text/csv",
                        "buffer": b"index,outcome\n0,1\n1,2\n2,3",
                    }
                },
            )
            assert first_response.ok, (
                f"Expected 200, got {first_response.status}: {first_response.text()}"
            )
            first_payload = first_response.json()
            dataset_id = first_payload["dataset_id"]
            assert first_payload["rows_imported"] == 3

            second_response = api_context.post(
                "/api/data/upload?dataset_kind=training&csv_separator=%2C",
                multipart={
                    "file": {
                        "name": f"{dataset_name.upper()}.csv",
                        "mimeType": "text/csv",
                        "buffer": b"index,outcome\n10,36\n11,35\n12,34\n13,33\n14,32",
                    }
                },
            )
            assert second_response.ok, (
                f"Expected 200, got {second_response.status}: {second_response.text()}"
            )
            second_payload = second_response.json()
            assert second_payload["dataset_id"] == dataset_id
            assert second_payload["dataset_name"] == dataset_name.upper()
            assert second_payload["rows_imported"] == 5

            summary_response = api_context.get("/api/datasets/training/summary")
            assert summary_response.ok
            matches = [
                item
                for item in summary_response.json().get("datasets", [])
                if item.get("dataset_name", "").casefold() == dataset_name.casefold()
            ]
            assert len(matches) == 1
            assert matches[0]["dataset_id"] == dataset_id
            assert matches[0]["row_count"] == 5
        finally:
            if isinstance(dataset_id, int):
                delete_uploaded_dataset(api_context, dataset_id)
