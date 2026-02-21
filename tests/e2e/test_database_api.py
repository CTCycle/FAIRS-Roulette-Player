"""
E2E tests for dataset listing APIs under /database/roulette-series.
"""

from playwright.sync_api import APIRequestContext


DATASET_NAME = "e2e_dataset_for_listing"


def ensure_dataset_for_listing(api_context: APIRequestContext) -> None:
    summary_response = api_context.get("/database/roulette-series/datasets/summary")
    assert summary_response.ok
    summary_payload = summary_response.json()
    datasets = summary_payload.get("datasets", [])
    existing = next(
        (item for item in datasets if item.get("dataset_name") == DATASET_NAME),
        None,
    )
    if existing is not None:
        return

    csv_content = b"idx,outcome\n0,0\n1,14\n2,28\n3,7\n4,22"
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
    assert upload_response.ok, (
        f"Expected 200, got {upload_response.status}: {upload_response.text()}"
    )


class TestRouletteDatasetsEndpoints:
    """Tests for /database/roulette-series/datasets endpoints."""

    def test_list_roulette_datasets(self, api_context: APIRequestContext):
        ensure_dataset_for_listing(api_context)
        response = api_context.get("/database/roulette-series/datasets")
        assert response.ok, f"Expected 200, got {response.status}"

        data = response.json()
        assert "datasets" in data
        assert isinstance(data["datasets"], list)
        assert data["datasets"], "Expected at least one dataset after setup."
        sample = data["datasets"][0]
        assert "dataset_id" in sample
        assert "dataset_name" in sample
        assert isinstance(sample["dataset_id"], int)
        assert isinstance(sample["dataset_name"], str)
        assert sample["dataset_name"]

    def test_list_roulette_datasets_summary(self, api_context: APIRequestContext):
        ensure_dataset_for_listing(api_context)
        response = api_context.get("/database/roulette-series/datasets/summary")
        assert response.ok, f"Expected 200, got {response.status}"

        data = response.json()
        assert "datasets" in data
        assert isinstance(data["datasets"], list)
        assert data["datasets"], "Expected at least one dataset after setup."
        sample = data["datasets"][0]
        assert "dataset_id" in sample
        assert "dataset_name" in sample
        assert "row_count" in sample
        assert isinstance(sample["dataset_id"], int)
        assert isinstance(sample["row_count"], int)
        assert sample["row_count"] >= 0
