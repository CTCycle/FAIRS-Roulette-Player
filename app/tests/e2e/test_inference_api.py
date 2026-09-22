"""
E2E tests for Inference API endpoints.
Tests: /inference/sessions/start, /inference/sessions/{id}/next,
       /inference/sessions/{id}/step, /inference/sessions/{id}/shutdown
"""

import pytest
from playwright.sync_api import APIRequestContext

VAL11_CHECKPOINT = "val00_lineage_20260921"
VAL11_DATASET_ID = 5

###############################################################################
def require_checkpoint(api_context: APIRequestContext) -> str:
    response = api_context.get("/api/training/checkpoints")
    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    checkpoints = response.json()
    if VAL11_CHECKPOINT not in checkpoints:
        pytest.skip(f"VAL-11 checkpoint {VAL11_CHECKPOINT!r} is not available.")
    return VAL11_CHECKPOINT

###############################################################################
def require_dataset_id(api_context: APIRequestContext) -> int:
    response = api_context.get("/api/datasets/training")
    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    datasets = response.json().get("datasets", [])
    dataset = next(
        (
            item
            for item in datasets
            if item.get("dataset_id") == VAL11_DATASET_ID
        ),
        None,
    )
    if dataset is None:
        pytest.skip(f"VAL-11 training dataset {VAL11_DATASET_ID} is not available.")
    return VAL11_DATASET_ID

###############################################################################
def start_inference_session(
    api_context: APIRequestContext,
    checkpoint: str,
    dataset_id: int,
    game_capital: int = 1000,
    game_bet: int = 10,
) -> dict:
    response = api_context.post(
        "/api/inference/sessions/start",
        data={
            "checkpoint": checkpoint,
            "dataset_id": dataset_id,
            "game_capital": game_capital,
            "game_bet": game_bet,
        },
    )
    if not response.ok:
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            payload = {}
        detail = (
            payload.get("detail", response.text())
            if isinstance(payload, dict)
            else response.text()
        )
        pytest.fail(
            f"Unable to start inference session with the VAL-11 lineage: {detail}",
            pytrace=False,
        )
    return response.json()

###############################################################################
def get_session_snapshot(
    api_context: APIRequestContext, session_id: str
) -> dict:
    response = api_context.get(f"/api/inference/sessions/{session_id}")
    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    return response.json()

###############################################################################
class TestInferenceEndpoints:
    """Tests for the /inference/* API endpoints."""

    # -------------------------------------------------------------------------
    def test_start_session_with_invalid_checkpoint_returns_404(
        self, api_context: APIRequestContext
    ):
        """POST /inference/sessions/start with invalid checkpoint should return 404."""
        response = api_context.post(
            "/api/inference/sessions/start",
            data={
                "checkpoint": "non_existent_checkpoint_xyz",
                "dataset_id": 999999,
                "game_capital": 1000,
                "game_bet": 10,
            },
        )
        # Expect 404 because checkpoint doesn't exist
        assert response.status == 404

        data = response.json()
        assert "detail" in data

    # -------------------------------------------------------------------------
    def test_get_next_prediction_invalid_session_returns_404(
        self, api_context: APIRequestContext
    ):
        """POST /inference/sessions/{invalid_id}/next should return 404."""
        response = api_context.post(
            "/api/inference/sessions/invalid_session_id_12345/next"
        )
        assert response.status == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    # -------------------------------------------------------------------------
    def test_submit_step_invalid_session_returns_404(
        self, api_context: APIRequestContext
    ):
        """POST /inference/sessions/{invalid_id}/step should return 404."""
        response = api_context.post(
            "/api/inference/sessions/invalid_session_id_12345/step",
            data={
                "extraction": 17,
            },
        )
        assert response.status == 404

    # -------------------------------------------------------------------------
    def test_shutdown_invalid_session_succeeds(self, api_context: APIRequestContext):
        """
        POST /inference/sessions/{invalid_id}/shutdown should succeed (idempotent).
        Shutting down a non-existent session should not fail.
        """
        response = api_context.post("/api/inference/sessions/any_session_id/shutdown")
        # The current implementation deletes from dict silently, so it returns 200
        assert response.ok

        data = response.json()
        assert data.get("status") == "closed"

    # -------------------------------------------------------------------------
    def test_update_bet_invalid_session_returns_404(
        self, api_context: APIRequestContext
    ):
        response = api_context.post(
            "/api/inference/sessions/invalid_session_id_12345/bet",
            data={"bet_amount": 25},
        )
        assert response.status == 404
        data = response.json()
        assert "detail" in data

    # -------------------------------------------------------------------------
    def test_clear_rows_on_unknown_session_is_idempotent(
        self, api_context: APIRequestContext
    ):
        response = api_context.post("/api/inference/sessions/non_existent/rows/clear")
        assert response.ok
        data = response.json()
        assert data.get("status") == "cleared"
        assert data.get("session_id") == "non_existent"

###############################################################################
class TestInferenceSessionFlow:
    """
    Integration tests for the full inference session lifecycle.
    These tests require a valid checkpoint to exist.
    """

    # -------------------------------------------------------------------------
    def test_full_inference_session_flow(self, api_context: APIRequestContext):
        """
        Tests the complete lifecycle: start -> step -> next -> shutdown.
        Uses the fixed VAL-00 training lineage when it is available.
        """
        checkpoint_name = require_checkpoint(api_context)
        dataset_id = require_dataset_id(api_context)
        start_data = start_inference_session(api_context, checkpoint_name, dataset_id)
        session_id = start_data["session_id"]
        assert isinstance(session_id, str) and session_id
        assert start_data.get("checkpoint") == checkpoint_name
        assert start_data.get("game_capital") == 1000
        assert start_data.get("game_bet") >= 1
        assert start_data.get("current_capital") <= 1000
        prediction = start_data.get("prediction")
        assert isinstance(prediction, dict)
        assert isinstance(prediction.get("action"), int)
        assert isinstance(prediction.get("description"), str)
        relative_preference = prediction.get("relative_preference")
        assert isinstance(relative_preference, (int, float))
        assert 0.0 <= float(relative_preference) <= 1.0
        assert "confidence" not in prediction

        try:
            initial_snapshot = get_session_snapshot(api_context, session_id)
            assert initial_snapshot.get("checkpoint") == checkpoint_name
            assert initial_snapshot.get("dataset_id") == dataset_id
            assert initial_snapshot.get("initial_capital") == 1000
            assert initial_snapshot.get("step_count") == 0
            assert initial_snapshot.get("prediction_pending") is True
            assert initial_snapshot.get("last_prediction") == prediction
            assert len(initial_snapshot.get("steps", [])) == 1

            bet_response = api_context.post(
                f"/api/inference/sessions/{session_id}/bet",
                data={"bet_amount": 25},
            )
            assert bet_response.ok, (
                f"Expected 200, got {bet_response.status}: {bet_response.text()}"
            )
            assert bet_response.json().get("bet_amount") == 25
            bet_snapshot = get_session_snapshot(api_context, session_id)
            assert bet_snapshot.get("current_bet") == 25
            assert bet_snapshot.get("step_count") == 0
            assert bet_snapshot["steps"][0].get("bet_amount") == 25

            # Submit the observed result for the initial prediction.
            step_response = api_context.post(
                f"/api/inference/sessions/{session_id}/step",
                data={
                    "extraction": 17,
                },
            )
            assert step_response.ok
            step_data = step_response.json()
            assert "step" in step_data
            assert "reward" in step_data
            assert "capital_after" in step_data
            assert step_data.get("session_id") == session_id
            assert step_data.get("step") == 1
            assert step_data.get("real_extraction") == 17
            assert isinstance(step_data.get("predicted_action"), int)
            assert isinstance(step_data.get("predicted_action_desc"), str)
            assert isinstance(step_data.get("reward"), int)
            assert isinstance(step_data.get("capital_after"), int)

            observed_snapshot = get_session_snapshot(api_context, session_id)
            assert observed_snapshot.get("step_count") == 1
            assert observed_snapshot.get("prediction_pending") is False
            assert observed_snapshot.get("current_capital") == step_data["capital_after"]
            assert len(observed_snapshot.get("steps", [])) == 1
            assert observed_snapshot["steps"][0].get("bet_amount") == 25
            assert observed_snapshot["steps"][0].get("observed_outcome_id") == 17
            assert observed_snapshot["steps"][0].get("reward") == step_data["reward"]
            assert (
                observed_snapshot["steps"][0].get("capital_after")
                == step_data["capital_after"]
            )

            # Request the next prediction only after the observed result.
            next_response = api_context.post(
                f"/api/inference/sessions/{session_id}/next"
            )
            assert next_response.ok
            next_data = next_response.json()
            assert "prediction" in next_data
            assert next_data["prediction"] is not None
            assert next_data.get("session_id") == session_id
            assert isinstance(next_data["prediction"].get("action"), int)
            assert isinstance(next_data["prediction"].get("description"), str)
            next_preference = next_data["prediction"].get("relative_preference")
            assert isinstance(next_preference, (int, float))
            assert 0.0 <= float(next_preference) <= 1.0
            assert "confidence" not in next_data["prediction"]

            next_snapshot = get_session_snapshot(api_context, session_id)
            assert next_snapshot.get("step_count") == 1
            assert next_snapshot.get("prediction_pending") is True
            assert next_snapshot.get("last_prediction") == next_data["prediction"]
            assert len(next_snapshot.get("steps", [])) == 2
            assert next_snapshot["steps"][0].get("observed_outcome_id") == 17
            assert next_snapshot["steps"][1].get("observed_outcome_id") is None

        finally:
            # Always shutdown the session
            shutdown_response = api_context.post(
                f"/api/inference/sessions/{session_id}/shutdown"
            )
            assert shutdown_response.ok, (
                f"Expected 200, got {shutdown_response.status}: {shutdown_response.text()}"
            )

    # -------------------------------------------------------------------------
    def test_inference_session_supports_bet_update_and_rows_clear(
        self, api_context: APIRequestContext
    ):
        checkpoint_name = require_checkpoint(api_context)
        dataset_id = require_dataset_id(api_context)
        start_data = start_inference_session(api_context, checkpoint_name, dataset_id)
        session_id = start_data["session_id"]

        try:
            bet_response = api_context.post(
                f"/api/inference/sessions/{session_id}/bet",
                data={"bet_amount": 25},
            )
            assert bet_response.ok, (
                f"Expected 200, got {bet_response.status}: {bet_response.text()}"
            )
            bet_payload = bet_response.json()
            assert bet_payload.get("session_id") == session_id
            assert bet_payload.get("bet_amount") == 25
            bet_snapshot = get_session_snapshot(api_context, session_id)
            assert bet_snapshot.get("current_bet") == 25
            assert bet_snapshot.get("step_count") == 0
            assert len(bet_snapshot.get("steps", [])) == 1

            shutdown_response = api_context.post(
                f"/api/inference/sessions/{session_id}/shutdown"
            )
            assert shutdown_response.ok

            clear_rows_response = api_context.post(
                f"/api/inference/sessions/{session_id}/rows/clear"
            )
            assert clear_rows_response.ok, (
                f"Expected 200, got {clear_rows_response.status}: {clear_rows_response.text()}"
            )
            clear_rows_payload = clear_rows_response.json()
            assert clear_rows_payload.get("session_id") == session_id
            assert clear_rows_payload.get("status") == "cleared"
        finally:
            api_context.post(f"/api/inference/sessions/{session_id}/shutdown")

    # -------------------------------------------------------------------------
    def test_clear_inference_context_removes_uploaded_inference_dataset(
        self, api_context: APIRequestContext
    ):
        """Run against isolated app data because context clear removes all uploads."""
        checkpoint_name = require_checkpoint(api_context)
        csv_content = b"outcome\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10"
        upload_response = api_context.post(
            "/api/data/upload?dataset_kind=inference&csv_separator=%2C",
            multipart={
                "file": {
                    "name": "val11_inference_context_clear.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content,
                }
            },
        )
        assert upload_response.ok, (
            f"Expected 200, got {upload_response.status}: {upload_response.text()}"
        )
        upload_payload = upload_response.json()
        dataset_id = upload_payload.get("dataset_id")
        assert isinstance(dataset_id, int) and dataset_id > 0

        clear_response = api_context.post("/api/inference/context/clear")
        assert clear_response.ok, (
            f"Expected 200, got {clear_response.status}: {clear_response.text()}"
        )
        clear_payload = clear_response.json()
        assert clear_payload.get("status") == "cleared"

        start_response = api_context.post(
            "/api/inference/sessions/start",
            data={
                "checkpoint": checkpoint_name,
                "dataset_id": dataset_id,
                "game_capital": 1000,
                "game_bet": 10,
            },
        )
        assert start_response.status == 404
        start_payload = start_response.json()
        assert "detail" in start_payload
        assert "dataset" in str(start_payload["detail"]).lower()

    # -------------------------------------------------------------------------
    def test_clear_inference_context_rejects_active_session(
        self, api_context: APIRequestContext
    ):
        checkpoint_name = require_checkpoint(api_context)
        dataset_id = require_dataset_id(api_context)
        start_data = start_inference_session(api_context, checkpoint_name, dataset_id)
        session_id = start_data["session_id"]

        try:
            clear_response = api_context.post("/api/inference/context/clear")
            assert clear_response.status == 409
            payload = clear_response.json()
            assert "active" in str(payload.get("detail", "")).lower()
        finally:
            shutdown_response = api_context.post(
                f"/api/inference/sessions/{session_id}/shutdown"
            )
            assert shutdown_response.ok
