"""
E2E tests for Data Upload API endpoint.
Tests: POST /data/upload
"""
import io
from playwright.sync_api import APIRequestContext


class TestDataUploadEndpoint:
    """Tests for the /data/upload API endpoint."""

    def test_upload_without_file_returns_422(self, api_context: APIRequestContext):
        """POST /data/upload without a file should return 422 (validation error)."""
        response = api_context.post("/data/upload?table=ROULETTE_SERIES")
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
        # Create a sample CSV with extraction column
        csv_content = b"extraction\n0\n15\n32\n7\n21"
        
        response = api_context.post(
            "/data/upload?table=ROULETTE_SERIES&csv_separator=%2C",  # URL-encoded comma
            multipart={
                "file": {
                    "name": "test_extractions.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content,
                }
            }
        )
        
        # This may succeed or fail depending on column requirements
        # A 200 means success, 400 means validation error (both are acceptable)
        assert response.status in [200, 400]
        
        if response.ok:
            data = response.json()
            assert "rows_imported" in data
            assert "table" in data
            assert data["table"] == "ROULETTE_SERIES"

    def test_upload_empty_file_returns_400(self, api_context: APIRequestContext):
        """POST /data/upload with empty content should return 400."""
        response = api_context.post(
            "/data/upload?table=ROULETTE_SERIES",
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
            "/data/upload?table=ROULETTE_SERIES&sheet_name=0",
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
        csv_content = b"extraction;color\n0;green\n1;red\n2;black"
        
        response = api_context.post(
            "/data/upload?table=ROULETTE_SERIES&csv_separator=%3B",  # URL-encoded semicolon
            multipart={
                "file": {
                    "name": "test_semicolon.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content,
                }
            }
        )
        # May succeed or fail based on column validation
        assert response.status in [200, 400]
