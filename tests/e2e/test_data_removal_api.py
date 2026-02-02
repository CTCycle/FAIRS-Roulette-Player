"""
E2E tests for dataset removal via database endpoints.
"""
from playwright.sync_api import APIRequestContext


DATASET_NAME = "e2e_dataset_delete"


class TestDatasetRemoval:
    """Tests for dataset deletion via /database/roulette-series/datasets."""

    def test_delete_dataset_after_upload(self, api_context: APIRequestContext):
        csv_content = b"extraction\n0\n12\n24\n36\n5"
        upload_response = api_context.post(
            "/data/upload?table=ROULETTE_SERIES&csv_separator=%2C",
            multipart={
                "file": {
                    "name": f"{DATASET_NAME}.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content,
                }
            },
        )
        assert upload_response.ok, f"Expected 200, got {upload_response.status}: {upload_response.text()}"

        summary_response = api_context.get("/database/roulette-series/datasets/summary")
        assert summary_response.ok
        summary = summary_response.json()
        datasets = summary.get("datasets", [])
        dataset_names = [item.get("dataset_name") for item in datasets]
        assert DATASET_NAME in dataset_names

        delete_response = api_context.delete(f"/database/roulette-series/datasets/{DATASET_NAME}")
        assert delete_response.ok
        delete_payload = delete_response.json()
        assert delete_payload.get("status") == "deleted"
        assert delete_payload.get("dataset_name") == DATASET_NAME

        summary_after_response = api_context.get("/database/roulette-series/datasets/summary")
        assert summary_after_response.ok
        summary_after = summary_after_response.json()
        datasets_after = summary_after.get("datasets", [])
        dataset_names_after = [item.get("dataset_name") for item in datasets_after]
        assert DATASET_NAME not in dataset_names_after
