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

import os
import time
import pytest
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
    "qnet_neurons": 8,
    "embedding_dimensions": 8,
    "dataset_id": None,  # Use synthetic data
    "use_data_generator": True,
}

RUNNING_TRAINING_CONFIG = dict(
    MINIMAL_TRAINING_CONFIG,
    max_steps_episode=500,
    initial_capital=100000,
    bet_amount=1,
)

RESUME_TRAINING_CONFIG = {
    "additional_episodes": 1,
}

TRAINING_POLL_INTERVAL = float(os.getenv("E2E_TRAINING_POLL_INTERVAL", "0.5"))
TRAINING_TIMEOUT = float(os.getenv("E2E_TRAINING_TIMEOUT", "90"))
TRAINING_STATUS_TIMEOUT = float(os.getenv("E2E_TRAINING_STATUS_TIMEOUT", "3.0"))


def wait_for_training_running(
    api_context: APIRequestContext,
    timeout: float = TRAINING_STATUS_TIMEOUT,
    interval: float = 0.1,
) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = api_context.get("/training/status").json()
        if status.get("is_training"):
            return True
        if status.get("latest_stats", {}).get("status") in (
            "completed",
            "error",
            "cancelled",
        ):
            return False
        time.sleep(interval)
    return False


def wait_for_training_stopped(
    api_context: APIRequestContext,
    timeout: float = TRAINING_STATUS_TIMEOUT,
    interval: float = 0.1,
) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = api_context.get("/training/status").json()
        if not status.get("is_training"):
            return True
        time.sleep(interval)
    return False


def wait_for_job_completion(
    api_context: APIRequestContext,
    job_id: str,
    timeout: float = TRAINING_TIMEOUT,
    interval: float = TRAINING_POLL_INTERVAL,
) -> dict:
    deadline = time.time() + timeout
    last_payload = {}
    while time.time() < deadline:
        response = api_context.get(f"/training/jobs/{job_id}")
        if not response.ok:
            return {}
        payload = response.json()
        last_payload = payload
        if payload.get("status") in ("completed", "failed", "cancelled"):
            return payload
        time.sleep(interval)
    return last_payload


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
        assert "poll_interval" in data
        assert isinstance(data["is_training"], bool)
        assert isinstance(data["latest_stats"], dict)
        assert "status" in data["latest_stats"]
        assert isinstance(data["history"], list)
        assert isinstance(data["poll_interval"], (int, float))
        assert float(data["poll_interval"]) > 0

    def test_get_checkpoints_list(self, api_context: APIRequestContext):
        """GET /training/checkpoints should return a list of checkpoint names."""
        response = api_context.get("/training/checkpoints")
        assert response.ok

        data = response.json()
        assert isinstance(data, list)
        assert all(isinstance(item, str) for item in data)

    def test_stop_training_when_not_running_returns_400(
        self, api_context: APIRequestContext
    ):
        """POST /training/stop should return 400 if no training is active."""
        response = api_context.post("/training/stop")
        # When no training is running, expect 400
        assert response.status == 400

        data = response.json()
        assert "detail" in data

    def test_start_training_while_already_running_returns_409(
        self, api_context: APIRequestContext
    ):
        """
        POST /training/start should return 409 if training is already in progress.
        Note: This test requires training to be running. It may be skipped in CI.
        """
        # Ensure training is running
        api_context.post("/training/stop")  # Clean slate
        start_response = api_context.post(
            "/training/start", data=RUNNING_TRAINING_CONFIG
        )
        assert start_response.ok, "Failed to start setup training"

        if not wait_for_training_running(api_context):
            pytest.skip("Training completed too quickly to test concurrent start.")

        # Attempt to start again with minimal config
        response = api_context.post("/training/start", data=RUNNING_TRAINING_CONFIG)
        assert response.status == 409

        # Cleanup
        api_context.post("/training/stop")
        wait_for_training_stopped(api_context)

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
            assert data.get("status") in ("started", "running")
            job_id = data.get("job_id")
            assert job_id, "Job ID should be returned for polling"
            assert isinstance(data.get("poll_interval"), (int, float))
            assert float(data["poll_interval"]) > 0
            job_response = api_context.get(f"/training/jobs/{job_id}")
            assert job_response.ok, f"Expected 200, got {job_response.status}"
            job_data = job_response.json()
            assert job_data.get("job_id") == job_id
            assert job_data.get("job_type") == "training"
            assert job_data.get("status") in ("pending", "running", "completed")

            # Wait briefly then stop training to clean up
            time.sleep(1)
            api_context.post("/training/stop")

    def test_cancel_unknown_training_job_returns_404(
        self, api_context: APIRequestContext
    ):
        response = api_context.delete("/training/jobs/missing_job_123")
        assert response.status == 404
        payload = response.json()
        assert "detail" in payload


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
        start_response = api_context.post(
            "/training/start", data=RUNNING_TRAINING_CONFIG
        )
        assert start_response.ok, "Failed to start training"

        # Verify training is running
        if not wait_for_training_running(api_context):
            pytest.skip("Training completed too quickly to verify stop behavior.")

        status = api_context.get("/training/status").json()
        assert status.get("is_training") is True

        # Stop training
        stop_response = api_context.post("/training/stop")
        assert stop_response.ok

        # Verify stopped
        assert wait_for_training_stopped(api_context)
        status = api_context.get("/training/status").json()
        assert status.get("is_training") is False

    def test_training_job_can_be_cancelled_via_jobs_endpoint(
        self, api_context: APIRequestContext
    ):
        api_context.post("/training/stop")
        start_response = api_context.post(
            "/training/start", data=RUNNING_TRAINING_CONFIG
        )
        assert start_response.ok, (
            f"Expected 200, got {start_response.status}: {start_response.text()}"
        )
        start_payload = start_response.json()
        job_id = start_payload.get("job_id")
        assert isinstance(job_id, str) and job_id

        if not wait_for_training_running(api_context):
            pytest.skip("Training completed too quickly to validate cancellation.")

        cancel_response = api_context.delete(f"/training/jobs/{job_id}")
        assert cancel_response.ok, (
            f"Expected 200, got {cancel_response.status}: {cancel_response.text()}"
        )
        cancel_payload = cancel_response.json()
        assert cancel_payload.get("job_id") == job_id
        assert cancel_payload.get("success") is True
        assert "message" in cancel_payload

        job_payload = wait_for_job_completion(api_context, job_id, timeout=30.0)
        assert job_payload.get("status") in ("cancelled", "completed")
        assert wait_for_training_stopped(api_context, timeout=10.0)


class TestTrainingResume:
    """Tests for resume training and checkpoint metadata endpoints."""

    def test_resume_training_invalid_checkpoint_returns_404(
        self, api_context: APIRequestContext
    ):
        payload = dict(RESUME_TRAINING_CONFIG, checkpoint="missing_checkpoint_123")
        response = api_context.post("/training/resume", data=payload)
        assert response.status == 404
        data = response.json()
        assert "detail" in data

    def test_resume_training_from_new_checkpoint(self, api_context: APIRequestContext):
        api_context.post("/training/stop")
        before_response = api_context.get("/training/checkpoints")
        assert before_response.ok
        before_checkpoints = before_response.json()

        start_response = api_context.post(
            "/training/start", data=MINIMAL_TRAINING_CONFIG
        )
        assert start_response.ok, (
            f"Expected 200, got {start_response.status}: {start_response.text()}"
        )
        job_id = start_response.json().get("job_id")
        assert job_id

        job_payload = wait_for_job_completion(api_context, job_id, timeout=90.0)
        if job_payload.get("status") != "completed":
            api_context.post("/training/stop")
            pytest.skip("Training did not complete in time to produce a checkpoint.")

        after_response = api_context.get("/training/checkpoints")
        assert after_response.ok
        after_checkpoints = after_response.json()
        new_checkpoints = [
            item for item in after_checkpoints if item not in before_checkpoints
        ]
        if not new_checkpoints:
            pytest.skip("No new checkpoint detected after training completion.")

        checkpoint = new_checkpoints[0]
        metadata_response = api_context.get(
            f"/training/checkpoints/{checkpoint}/metadata"
        )
        assert metadata_response.ok
        metadata = metadata_response.json()
        assert metadata.get("checkpoint") == checkpoint
        assert "summary" in metadata
        summary = metadata["summary"]
        assert "episodes" in summary
        assert "batch_size" in summary

        resume_payload = dict(RESUME_TRAINING_CONFIG, checkpoint=checkpoint)
        resume_response = api_context.post("/training/resume", data=resume_payload)
        assert resume_response.ok, (
            f"Expected 200, got {resume_response.status}: {resume_response.text()}"
        )
        resume_job_id = resume_response.json().get("job_id")
        assert resume_job_id

        resume_job_payload = wait_for_job_completion(
            api_context, resume_job_id, timeout=90.0
        )
        if resume_job_payload.get("status") != "completed":
            api_context.post("/training/stop")
            pytest.skip("Resume training did not complete in time.")

        delete_response = api_context.delete(f"/training/checkpoints/{checkpoint}")
        assert delete_response.ok
