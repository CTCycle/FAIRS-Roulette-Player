"""
E2E tests for dataset removal via database endpoints.
"""
from playwright.sync_api import APIRequestContext


DATASET_NAME = "e2e_dataset_delete"


class TestDatasetRemoval:
    """Tests for dataset deletion via /database/roulette-series/datasets."""

    def test_delete_dataset_after_upload(self, api_context: APIRequestContext):
        csv_content = b"idx,outcome\n0,0\n1,12\n2,24\n3,36\n4,5"
        upload_response = api_context.post(
            "/data/upload?table=roulette_series&csv_separator=%2C",
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
        dataset_entry = next(
            (
                item
                for item in datasets
                if item.get("dataset_name") == DATASET_NAME
            ),
            None,
        )
        assert dataset_entry is not None
        dataset_id = dataset_entry.get("dataset_id")
        assert isinstance(dataset_id, str) and dataset_id

        delete_response = api_context.delete(f"/database/roulette-series/datasets/{dataset_id}")
        assert delete_response.ok
        delete_payload = delete_response.json()
        assert delete_payload.get("status") == "deleted"
        assert delete_payload.get("dataset_id") == dataset_id

        summary_after_response = api_context.get("/database/roulette-series/datasets/summary")
        assert summary_after_response.ok
        summary_after = summary_after_response.json()
        datasets_after = summary_after.get("datasets", [])
        names_after = [item.get("dataset_name") for item in datasets_after]
        assert DATASET_NAME not in names_after
