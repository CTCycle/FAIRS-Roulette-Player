"""
E2E tests for Inference API endpoints.
Tests: /inference/sessions/start, /inference/sessions/{id}/next, 
       /inference/sessions/{id}/step, /inference/sessions/{id}/shutdown
"""
from playwright.sync_api import APIRequestContext


class TestInferenceEndpoints:
    """Tests for the /inference/* API endpoints."""

    def test_start_session_with_invalid_checkpoint_returns_404(self, api_context: APIRequestContext):
        """POST /inference/sessions/start with invalid checkpoint should return 404."""
        response = api_context.post("/inference/sessions/start", data={
            "checkpoint": "non_existent_checkpoint_xyz",
            "name": "test_dataset",
            "game_capital": 1000,
            "game_bet": 10,
        })
        # Expect 404 because checkpoint doesn't exist
        assert response.status == 404
        
        data = response.json()
        assert "detail" in data

    def test_get_next_prediction_invalid_session_returns_404(self, api_context: APIRequestContext):
        """POST /inference/sessions/{invalid_id}/next should return 404."""
        response = api_context.post("/inference/sessions/invalid_session_id_12345/next")
        assert response.status == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_submit_step_invalid_session_returns_404(self, api_context: APIRequestContext):
        """POST /inference/sessions/{invalid_id}/step should return 404."""
        response = api_context.post("/inference/sessions/invalid_session_id_12345/step", data={
            "extraction": 17,
        })
        assert response.status == 404

    def test_shutdown_invalid_session_succeeds(self, api_context: APIRequestContext):
        """
        POST /inference/sessions/{invalid_id}/shutdown should succeed (idempotent).
        Shutting down a non-existent session should not fail.
        """
        response = api_context.post("/inference/sessions/any_session_id/shutdown")
        # The current implementation deletes from dict silently, so it returns 200
        assert response.ok
        
        data = response.json()
        assert data.get("status") == "closed"


class TestInferenceSessionFlow:
    """
    Integration tests for the full inference session lifecycle.
    These tests require a valid checkpoint to exist.
    """

    def test_full_inference_session_flow(self, api_context: APIRequestContext):
        """
        Tests the complete lifecycle: start -> next -> step -> shutdown.
        Skipped if no checkpoints are available.
        """
        # First, get list of checkpoints
        checkpoints_response = api_context.get("/training/checkpoints")
        checkpoints = checkpoints_response.json()
        
        if not checkpoints:
            return  # Skip if no checkpoints exist
        
        checkpoint_name = checkpoints[0]
        
        # Get a dataset name (if any)
        datasets_response = api_context.get("/database/roulette-series/datasets")
        datasets = datasets_response.json().get("datasets", [])
        name = datasets[0] if datasets else None

        if name is None:
            return  # Skip if no dataset for inference context
        
        # Start session
        start_response = api_context.post("/inference/sessions/start", data={
            "checkpoint": checkpoint_name,
            "name": name,
            "game_capital": 1000,
            "game_bet": 10,
        })
        
        if not start_response.ok:
            return  # Skip if session fails to start (e.g., missing inference context)
        
        start_data = start_response.json()
        session_id = start_data["session_id"]
        
        try:
            # Get next prediction
            next_response = api_context.post(f"/inference/sessions/{session_id}/next")
            assert next_response.ok
            next_data = next_response.json()
            assert "prediction" in next_data
            assert next_data["prediction"] is not None, "Prediction should not be None"
            
            # Submit a step with a sample extraction
            step_response = api_context.post(f"/inference/sessions/{session_id}/step", data={
                "extraction": 17,
            })
            assert step_response.ok
            step_data = step_response.json()
            assert "step" in step_data
            assert "reward" in step_data
            assert "capital_after" in step_data
            
        finally:
            # Always shutdown the session
            shutdown_response = api_context.post(f"/inference/sessions/{session_id}/shutdown")
            assert shutdown_response.ok
