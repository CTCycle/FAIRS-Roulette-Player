"""
E2E tests for training polling.
Tests the /training/status endpoint used by the UI.
"""


class TestTrainingPolling:
    """Tests for polling-based training status."""

    def test_training_status_polling_payload(self, api_context):
        response = api_context.get("/training/status")
        assert response.ok, f"Expected 200, got {response.status}"

        data = response.json()
        assert "is_training" in data
        assert "latest_stats" in data
        assert "history" in data
        assert "poll_interval" in data
        assert isinstance(data["is_training"], bool)
        assert isinstance(data["latest_stats"], dict)
        assert isinstance(data["history"], list)
        assert isinstance(data["poll_interval"], (int, float))
        assert float(data["poll_interval"]) > 0
