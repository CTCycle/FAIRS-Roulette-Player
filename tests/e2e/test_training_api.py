"""
E2E tests for Training API endpoints.
Tests: /training/start, /training/status, /training/stop, /training/checkpoints

NOTE: Training tests use minimal configurations to ensure fast test execution:
- episodes: 1
- max_steps_episode: 100 (minimum allowed by schema)
- num_generated_samples: 100 (minimum allowed)
- batch_size: 1
- replay_buffer_size: 100 (minimum allowed)
"""
import time
from playwright.sync_api import APIRequestContext


# Minimal training configuration for fast tests
MINIMAL_TRAINING_CONFIG = {
    "episodes": 1,
    "max_steps_episode": 100,
    "num_generated_samples": 100,
    "batch_size": 1,
    "replay_buffer_size": 100,
    "max_memory_size": 100,
    "perceptive_field_size": 8,
    "QNet_neurons": 8,
    "embedding_dimensions": 8,
    "dataset_name": None,  # Use synthetic data
    "use_data_generator": True,
}


class TestTrainingEndpoints:
    """Tests for the /training/* API endpoints."""

    def test_get_training_status(self, api_context: APIRequestContext):
        """GET /training/status should return current training state."""
        response = api_context.get("/training/status")
        assert response.ok, f"Expected 200, got {response.status}"
        
        data = response.json()
        assert "is_training" in data
        assert "latest_stats" in data
        assert "history" in data
        assert isinstance(data["is_training"], bool)

    def test_get_checkpoints_list(self, api_context: APIRequestContext):
        """GET /training/checkpoints should return a list of checkpoint names."""
        response = api_context.get("/training/checkpoints")
        assert response.ok
        
        data = response.json()
        assert isinstance(data, list)

    def test_stop_training_when_not_running_returns_400(self, api_context: APIRequestContext):
        """POST /training/stop should return 400 if no training is active."""
        response = api_context.post("/training/stop")
        # When no training is running, expect 400
        assert response.status == 400
        
        data = response.json()
        assert "detail" in data

    def test_start_training_while_already_running_returns_409(self, api_context: APIRequestContext):
        """
        POST /training/start should return 409 if training is already in progress.
        Note: This test requires training to be running. It may be skipped in CI.
        """
        # Ensure training is running
        api_context.post("/training/stop") # Clean slate
        start_response = api_context.post("/training/start", data=MINIMAL_TRAINING_CONFIG)
        assert start_response.ok, "Failed to start setup training"
        
        # Attempt to start again with minimal config
        response = api_context.post("/training/start", data=MINIMAL_TRAINING_CONFIG)
        assert response.status == 409
        
        # Cleanup
        api_context.post("/training/stop")

    def test_start_training_with_minimal_config(self, api_context: APIRequestContext):
        """
        POST /training/start with minimal config should start training.
        Uses smallest possible values to minimize test duration.
        """
        # Check if training is already running
        # Ensure clean state
        api_context.post("/training/stop")
        
        # Start training with minimal config
        response = api_context.post("/training/start", data=MINIMAL_TRAINING_CONFIG)
        
        # Should succeed
        assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
        
        if response.ok:
            data = response.json()
            assert data.get("status") == "started"
            
            # Wait briefly then stop training to clean up
            time.sleep(1)
            api_context.post("/training/stop")


class TestTrainingLifecycle:
    """Integration tests for training start/stop lifecycle."""

    def test_training_can_be_stopped(self, api_context: APIRequestContext):
        """
        Tests that training can be started and stopped.
        Uses minimal configuration for speed.
        """
        # Skip if training already running
        # Ensure clean state
        api_context.post("/training/stop")
        
        # Start training
        start_response = api_context.post("/training/start", data=MINIMAL_TRAINING_CONFIG)
        assert start_response.ok, "Failed to start training"
        
        # Verify training is running
        time.sleep(0.5)
        status = api_context.get("/training/status").json()
        assert status.get("is_training") is True
        
        # Stop training
        stop_response = api_context.post("/training/stop")
        assert stop_response.ok
        
        # Verify stopped
        status = api_context.get("/training/status").json()
        assert status.get("is_training") is False
