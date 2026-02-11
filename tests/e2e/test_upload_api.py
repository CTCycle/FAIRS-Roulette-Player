"""
E2E tests for Data Upload API endpoint.
Tests: POST /data/upload
"""
from playwright.sync_api import APIRequestContext


def load_dataset_summary_entry(
    api_context: APIRequestContext, dataset_id: int
) -> dict | None:
    response = api_context.get("/database/roulette-series/datasets/summary")
    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    datasets = response.json().get("datasets", [])
    return next(
        (
            item
            for item in datasets
            if item.get("dataset_id") == dataset_id
        ),
        None,
    )


class TestDataUploadEndpoint:
    """Tests for the /data/upload API endpoint."""

    def test_upload_without_file_returns_422(self, api_context: APIRequestContext):
        """POST /data/upload without a file should return 422 (validation error)."""
        response = api_context.post("/data/upload?table=roulette_series")
        # FastAPI returns 422 for missing required fields
        assert response.status == 422

    def test_upload_with_invalid_table_returns_422(self, api_context: APIRequestContext):
        """POST /data/upload with an invalid table name should return 422."""
        # Create a minimal CSV in memory
        csv_content = b"extraction\n1\n2\n3"
        
        response = api_context.post(
            "/data/upload?table=INVALID_TABLE_NAME",
            multipart={
                "file": {
                    "name": "test.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content,
                }
            }
        )
        # Invalid table enum value should fail validation
        assert response.status == 422

    def test_upload_valid_csv_to_roulette_series(self, api_context: APIRequestContext):
        """POST /data/upload with valid CSV should import data successfully."""
        csv_content = b"draw_index,observed_outcome\n0,0\n1,15\n2,32\n3,7\n4,21"
        
        response = api_context.post(
            "/data/upload?table=roulette_series&csv_separator=%2C",  # URL-encoded comma
            multipart={
                "file": {
                    "name": "test_extractions.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content,
                }
            }
        )
        
        # This should succeed for a valid CSV
        assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
        
        data = response.json()
        assert "rows_imported" in data
        assert "table" in data
        assert "dataset_id" in data
        assert "dataset_kind" in data
        assert data["table"] == "roulette_series"
        assert data["dataset_kind"] == "training"
        assert data["rows_imported"] == 5
        assert isinstance(data["dataset_id"], int)

    def test_upload_empty_file_returns_400(self, api_context: APIRequestContext):
        """POST /data/upload with empty content should return 400."""
        response = api_context.post(
            "/data/upload?table=roulette_series",
            multipart={
                "file": {
                    "name": "empty.csv",
                    "mimeType": "text/csv",
                    "buffer": b"",
                }
            }
        )
        # Empty file should fail parsing
        assert response.status == 400


class TestDataUploadEdgeCases:
    """Edge case tests for data upload functionality."""

    def test_upload_xlsx_format(self, api_context: APIRequestContext):
        """POST /data/upload should support XLSX files."""
        # Note: Creating a real XLSX in tests is complex; this test verifies
        # the endpoint accepts the format but may fail on parsing
        response = api_context.post(
            "/data/upload?table=roulette_series&sheet_name=0",
            multipart={
                "file": {
                    "name": "test.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "buffer": b"not a real xlsx",  # Will fail parsing
                }
            }
        )
        # Expect 400 because it's not a valid XLSX
        assert response.status == 400

    def test_upload_with_custom_separator(self, api_context: APIRequestContext):
        """POST /data/upload should respect csv_separator parameter."""
        # CSV with semicolon separator
        csv_content = b"index;value\n0;0\n1;32\n2;15"
        
        response = api_context.post(
            "/data/upload?table=roulette_series&csv_separator=%3B",  # URL-encoded semicolon
            multipart={
                "file": {
                    "name": "test_semicolon.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content,
                }
            }
        )
        # This should succeed if the separator is handled correctly
        assert response.ok, f"Expected 200, got {response.status}: {response.text()}"

    def test_upload_filters_invalid_outcomes_and_enriches_all_valid_rows(
        self, api_context: APIRequestContext
    ):
        """POST /data/upload should discard invalid outcomes and enrich valid rows."""
        dataset_name = "test_invalid_outcomes_cleanup"
        existing_response = api_context.get("/database/roulette-series/datasets/summary")
        if existing_response.ok:
            existing = existing_response.json().get("datasets", [])
            match = next(
                (
                    item
                    for item in existing
                    if item.get("dataset_name") == dataset_name
                ),
                None,
            )
            if match and match.get("dataset_id"):
                api_context.delete(
                    f"/database/roulette-series/datasets/{match['dataset_id']}"
                )
        csv_content = (
            b"spin,result\n"
            b"10,5\n"
            b"11,37\n"
            b"12,-1\n"
            b"13,0\n"
            b"14,36\n"
            b"15,abc\n"
            b"16,7.2\n"
            b"17,7\n"
        )

        response = api_context.post(
            "/data/upload?table=roulette_series&csv_separator=%2C",
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
        assert payload["rows_imported"] == 4
        dataset_id = payload.get("dataset_id")
        assert isinstance(dataset_id, int) and dataset_id > 0

        summary_entry = load_dataset_summary_entry(api_context, dataset_id)
        assert summary_entry is not None
        assert summary_entry.get("row_count") == 4
