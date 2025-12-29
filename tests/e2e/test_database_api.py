"""
E2E tests for Database API endpoints.
Tests: /database/tables, /database/tables/{name}, /database/tables/{name}/stats
"""
import re
from playwright.sync_api import APIRequestContext, expect


class TestDatabaseEndpoints:
    """Tests for the /database/* API endpoints."""

    def test_list_tables_returns_expected_tables(self, api_context: APIRequestContext):
        """GET /database/tables should return the list of available tables."""
        response = api_context.get("/database/tables")
        assert response.ok, f"Expected 200, got {response.status}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check that expected tables are present
        table_names = [t["name"] for t in data]
        assert "ROULETTE_SERIES" in table_names
        assert "PREDICTED_GAMES" in table_names
        assert "CHECKPOINTS_SUMMARY" in table_names

    def test_get_table_data_valid_table(self, api_context: APIRequestContext):
        """GET /database/tables/{table_name} should return paginated data."""
        response = api_context.get("/database/tables/ROULETTE_SERIES")
        assert response.ok, f"Expected 200, got {response.status}"
        
        data = response.json()
        assert "columns" in data
        assert "rows" in data
        assert "offset" in data
        assert "limit" in data
        assert isinstance(data["columns"], list)
        assert isinstance(data["rows"], list)

    def test_get_table_data_with_offset(self, api_context: APIRequestContext):
        """GET /database/tables/{table_name}?offset=N should support pagination."""
        response = api_context.get("/database/tables/ROULETTE_SERIES?offset=10")
        assert response.ok
        
        data = response.json()
        assert data["offset"] == 10

    def test_get_table_data_invalid_table_returns_404(self, api_context: APIRequestContext):
        """GET /database/tables/{invalid} should return 404."""
        response = api_context.get("/database/tables/NON_EXISTENT_TABLE")
        assert response.status == 404

    def test_get_table_stats_valid_table(self, api_context: APIRequestContext):
        """GET /database/tables/{table_name}/stats should return row/column counts."""
        response = api_context.get("/database/tables/ROULETTE_SERIES/stats")
        assert response.ok
        
        data = response.json()
        assert "table_name" in data
        assert "row_count" in data
        assert "column_count" in data
        assert data["table_name"] == "ROULETTE_SERIES"

    def test_get_table_stats_invalid_table_returns_404(self, api_context: APIRequestContext):
        """GET /database/tables/{invalid}/stats should return 404."""
        response = api_context.get("/database/tables/FAKE_TABLE/stats")
        assert response.status == 404

    def test_list_roulette_datasets(self, api_context: APIRequestContext):
        """GET /database/roulette-series/datasets should return dataset names."""
        response = api_context.get("/database/roulette-series/datasets")
        assert response.ok
        
        data = response.json()
        assert "datasets" in data
        assert isinstance(data["datasets"], list)
