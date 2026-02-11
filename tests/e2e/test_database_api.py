"""
E2E tests for dataset listing APIs under /database/roulette-series.
"""
from playwright.sync_api import APIRequestContext


class TestRouletteDatasetsEndpoints:
    """Tests for /database/roulette-series/datasets endpoints."""

    def test_list_roulette_datasets(self, api_context: APIRequestContext):
        response = api_context.get("/database/roulette-series/datasets")
        assert response.ok, f"Expected 200, got {response.status}"

        data = response.json()
        assert "datasets" in data
        assert isinstance(data["datasets"], list)
        if data["datasets"]:
            sample = data["datasets"][0]
            assert "dataset_id" in sample
            assert "dataset_name" in sample
            assert isinstance(sample["dataset_id"], int)

    def test_list_roulette_datasets_summary(self, api_context: APIRequestContext):
        response = api_context.get("/database/roulette-series/datasets/summary")
        assert response.ok, f"Expected 200, got {response.status}"

        data = response.json()
        assert "datasets" in data
        assert isinstance(data["datasets"], list)
        if data["datasets"]:
            sample = data["datasets"][0]
            assert "dataset_id" in sample
            assert "dataset_name" in sample
            assert "row_count" in sample
            assert isinstance(sample["dataset_id"], int)
