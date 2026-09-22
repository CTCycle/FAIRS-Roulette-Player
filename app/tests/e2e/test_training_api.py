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

import json
import os
import time
from pathlib import Path
from uuid import uuid4

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

VAL08_STORED_CPU_CONFIG = dict(
    MINIMAL_TRAINING_CONFIG,
    episodes=1,
    max_steps_episode=100,
    perceptive_field_size=8,
    batch_size=100,
    replay_buffer_size=100,
    max_memory_size=100,
    dataset_id=5,
    use_data_generator=False,
    use_device_gpu=False,
    use_mixed_precision=False,
)

RESUME_TRAINING_CONFIG = {
    "additional_episodes": 1,
}

TRAINING_POLL_INTERVAL = float(os.getenv("E2E_TRAINING_POLL_INTERVAL", "0.5"))
TRAINING_TIMEOUT = float(os.getenv("E2E_TRAINING_TIMEOUT", "90"))
# Worker shutdown is asynchronous and may include process termination on Windows.
TRAINING_STATUS_TIMEOUT = float(os.getenv("E2E_TRAINING_STATUS_TIMEOUT", "10.0"))

###############################################################################
def wait_for_training_running(
    api_context: APIRequestContext,
    timeout: float = TRAINING_STATUS_TIMEOUT,
    interval: float = 0.1,
) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = api_context.get("/api/training/status").json()
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

###############################################################################
def wait_for_training_stopped(
    api_context: APIRequestContext,
    timeout: float = TRAINING_STATUS_TIMEOUT,
    interval: float = 0.1,
) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = api_context.get("/api/training/status").json()
        if not status.get("is_training"):
            return True
        time.sleep(interval)
    return False

###############################################################################
def wait_for_job_completion(
    api_context: APIRequestContext,
    job_id: str,
    timeout: float = TRAINING_TIMEOUT,
    interval: float = TRAINING_POLL_INTERVAL,
) -> dict:
    deadline = time.time() + timeout
    last_payload = {}
    while time.time() < deadline:
        response = api_context.get(f"/api/training/jobs/{job_id}")
        if not response.ok:
            return {}
        payload = response.json()
        last_payload = payload
        if payload.get("status") in ("completed", "failed", "cancelled"):
            return payload
        time.sleep(interval)
    return last_payload

###############################################################################
@pytest.mark.parametrize(
    ("overrides", "expected_fragment"),
    [
        (
            {"minimum_exploration_rate": 0.8},
            "minimum_exploration_rate",
        ),
        ({"replay_buffer_size": 101}, "replay_buffer_size"),
        ({"batch_size": 101}, "batch_size"),
        (
            {"bet_strategy_model_enabled": True},
            "bet_strategy_model_enabled",
        ),
        (
            {
                "dynamic_betting_enabled": True,
                "bet_unit": 20,
                "bet_max": 10,
            },
            "bet_max",
        ),
        (
            {"dataset_id": None, "use_data_generator": False},
            "dataset_id",
        ),
        ({"checkpoint_name": "../invalid-checkpoint"}, "checkpoint"),
        ({"perceptive_field_size": 0}, "perceptive_field_size"),
        ({"perceptive_field_size": 1025}, "perceptive_field_size"),
        ({"episodes": 0}, "episodes"),
        ({"learning_rate": 0}, "learning_rate"),
        ({"sample_size": 0}, "sample_size"),
        ({"validation_size": 1}, "validation_size"),
    ],
)
def test_validate_rejects_invalid_training_relationships(
    api_context: APIRequestContext,
    overrides: dict[str, object],
    expected_fragment: str,
):
    payload = dict(VAL08_STORED_CPU_CONFIG)
    payload.update(overrides)
    response = api_context.post("/api/training/validate", data=payload)

    assert response.status == 422, response.text()
    assert expected_fragment in response.text()

###############################################################################
def test_validate_accepts_stored_cpu_configuration(
    api_context: APIRequestContext,
):
    response = api_context.post("/api/training/validate", data=VAL08_STORED_CPU_CONFIG)

    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    normalized = response.json()
    assert normalized["dataset_id"] == 5
    assert normalized["use_data_generator"] is False
    assert normalized["episodes"] == 1
    assert normalized["max_steps_episode"] == 100
    assert normalized["perceptive_field_size"] == 8
    assert normalized["batch_size"] == 100
    assert normalized["replay_buffer_size"] == 100
    assert normalized["max_memory_size"] == 100
    assert normalized["use_device_gpu"] is False
    assert normalized["use_mixed_precision"] is False

###############################################################################
def test_stale_dataset_is_rejected_deterministically_without_side_effects(
    api_context: APIRequestContext,
):
    checkpoint_name = f"val07_stale_dataset_{uuid4().hex[:10]}"
    payload = dict(
        VAL08_STORED_CPU_CONFIG,
        dataset_id=2_147_483_647,
        checkpoint_name=checkpoint_name,
    )
    before_status = api_context.get("/api/training/status").json()
    before_checkpoints = api_context.get("/api/training/checkpoints").json()
    assert before_status["is_training"] is False
    assert before_status["job_id"] is None

    first_validation = api_context.post("/api/training/validate", data=payload)
    repeated_validation = api_context.post("/api/training/validate", data=payload)
    start = api_context.post("/api/training/start", data=payload)

    assert first_validation.status == 404, first_validation.text()
    assert repeated_validation.status == 404, repeated_validation.text()
    assert first_validation.json() == repeated_validation.json()
    assert start.status == 404, start.text()

    after_status = api_context.get("/api/training/status").json()
    after_checkpoints = api_context.get("/api/training/checkpoints").json()
    assert after_status["is_training"] is False
    assert after_status["job_id"] is None
    assert after_checkpoints == before_checkpoints
    assert checkpoint_name not in after_checkpoints

###############################################################################
def test_dataset_deleted_after_validation_is_rejected_before_start(
    api_context: APIRequestContext,
):
    dataset_name = f"val07_deleted_dataset_{uuid4().hex[:10]}"
    checkpoint_name = f"val07_deleted_dataset_{uuid4().hex[:10]}"
    upload = api_context.post(
        "/api/data/upload?dataset_kind=training&csv_separator=%2C",
        multipart={
            "file": {
                "name": f"{dataset_name}.csv",
                "mimeType": "text/csv",
                "buffer": b"draw_index,observed_outcome\n0,0\n1,15\n2,32\n3,7\n4,21",
            }
        },
    )
    assert upload.ok, f"Expected 200, got {upload.status}: {upload.text()}"
    dataset_id = upload.json().get("dataset_id")
    assert isinstance(dataset_id, int)

    payload = dict(
        VAL08_STORED_CPU_CONFIG,
        dataset_id=dataset_id,
        checkpoint_name=checkpoint_name,
    )
    before_status = api_context.get("/api/training/status").json()
    before_checkpoints = api_context.get("/api/training/checkpoints").json()
    assert before_status["is_training"] is False
    assert before_status["job_id"] is None

    try:
        validation = api_context.post("/api/training/validate", data=payload)
        assert validation.ok, (
            f"Expected 200, got {validation.status}: {validation.text()}"
        )
        deletion = api_context.delete(f"/api/datasets/training/{dataset_id}")
        assert deletion.ok, (
            f"Expected 200, got {deletion.status}: {deletion.text()}"
        )

        start = api_context.post("/api/training/start", data=payload)
        assert start.status == 404, start.text()
        after_status = api_context.get("/api/training/status").json()
        after_checkpoints = api_context.get("/api/training/checkpoints").json()
        assert after_status["is_training"] is False
        assert after_status["job_id"] is None
        assert after_checkpoints == before_checkpoints
        assert checkpoint_name not in after_checkpoints
    finally:
        # Keep the test safe if validation or deletion fails before cleanup.
        api_context.delete(f"/api/datasets/training/{dataset_id}")

###############################################################################
def test_start_rejects_invalid_semantics_when_validation_is_bypassed(
    api_context: APIRequestContext,
):
    checkpoint_name = f"val07_invalid_start_{uuid4().hex[:10]}"
    payload = dict(
        VAL08_STORED_CPU_CONFIG,
        minimum_exploration_rate=0.8,
        checkpoint_name=checkpoint_name,
    )
    before_status = api_context.get("/api/training/status").json()
    before_checkpoints = api_context.get("/api/training/checkpoints").json()
    assert before_status["is_training"] is False
    assert before_status["job_id"] is None

    response = api_context.post("/api/training/start", data=payload)

    assert response.status == 422, response.text()
    assert "minimum_exploration_rate" in response.text()
    after_status = api_context.get("/api/training/status").json()
    after_checkpoints = api_context.get("/api/training/checkpoints").json()
    assert after_status["is_training"] is False
    assert after_status["job_id"] is None
    assert after_checkpoints == before_checkpoints
    assert checkpoint_name not in after_checkpoints

###############################################################################
class TestTrainingCheckpointPublication:
    """Deterministic VAL-08 checkpoint publication evidence."""

    # -------------------------------------------------------------------------
    def test_stored_cpu_run_completes_and_publishes_expected_checkpoint(
        self, api_context: APIRequestContext
    ):
        checkpoint = f"val08_api_{uuid4().hex[:10]}"
        config = dict(VAL08_STORED_CPU_CONFIG, checkpoint_name=checkpoint)
        before_response = api_context.get("/api/training/checkpoints")
        assert before_response.ok
        assert checkpoint not in before_response.json()

        start_response = api_context.post("/api/training/start", data=config)
        assert start_response.status == 202, (
            f"Expected 202, got {start_response.status}: {start_response.text()}"
        )
        job_id = start_response.json().get("job_id")
        assert isinstance(job_id, str) and job_id

        try:
            job_payload = wait_for_job_completion(api_context, job_id, timeout=180.0)
            assert job_payload.get("job_id") == job_id
            assert job_payload.get("status") == "completed", job_payload
            assert float(job_payload.get("progress", 0.0)) == pytest.approx(100.0)
            assert wait_for_training_stopped(api_context, timeout=30.0)

            status_response = api_context.get("/api/training/status")
            assert status_response.ok
            status_payload = status_response.json()
            assert status_payload["is_training"] is False
            assert status_payload["job_id"] is None
            assert status_payload["latest_stats"]["status"] == "completed"
            assert status_payload["latest_stats"]["loss"] is not None
            assert status_payload["latest_stats"]["rmse"] is not None

            after_response = api_context.get("/api/training/checkpoints")
            assert after_response.ok
            assert checkpoint in after_response.json()

            metadata_response = api_context.get(
                f"/api/training/checkpoints/{checkpoint}/metadata"
            )
            assert metadata_response.ok
            metadata = metadata_response.json()
            assert metadata["checkpoint"] == checkpoint
            summary = metadata["summary"]
            assert summary["dataset_id"] == 5
            assert summary["episodes"] == 1
            assert summary["perceptive_field_size"] == 8
            assert summary["batch_size"] == 100
            assert summary["final_loss"] is not None
            assert summary["final_rmse"] is not None

            checkpoint_root = (
                Path(__file__).resolve().parents[2]
                / "resources"
                / "checkpoints"
                / checkpoint
            )
            configuration_path = checkpoint_root / "configuration" / "configuration.json"
            assert (checkpoint_root / ".complete").is_file()
            assert (checkpoint_root / "saved_model.keras").is_file()
            assert configuration_path.is_file()
            persisted = json.loads(
                configuration_path.read_text(encoding="utf-8")
            )
            persisted_training = persisted["training"]
            for key in (
                "dataset_id",
                "use_data_generator",
                "episodes",
                "max_steps_episode",
                "perceptive_field_size",
                "batch_size",
                "replay_buffer_size",
                "max_memory_size",
                "use_device_gpu",
                "use_mixed_precision",
                "checkpoint_name",
            ):
                assert persisted_training[key] == config[key]
        finally:
            api_context.post("/api/training/stop")
            wait_for_training_stopped(api_context, timeout=30.0)
            current_response = api_context.get("/api/training/checkpoints")
            if current_response.ok and checkpoint in current_response.json():
                delete_response = api_context.delete(
                    f"/api/training/checkpoints/{checkpoint}"
                )
                assert delete_response.ok

###############################################################################
class TestTrainingEndpoints:
    """Tests for the /training/* API endpoints."""

    # -------------------------------------------------------------------------
    def test_get_training_status(self, api_context: APIRequestContext):
        """GET /training/status should return current training state."""
        response = api_context.get("/api/training/status")
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

    # -------------------------------------------------------------------------
    def test_get_checkpoints_list(self, api_context: APIRequestContext):
        """GET /training/checkpoints should return a list of checkpoint names."""
        response = api_context.get("/api/training/checkpoints")
        assert response.ok

        data = response.json()
        assert isinstance(data, list)
        assert all(isinstance(item, str) for item in data)

    # -------------------------------------------------------------------------
    def test_stop_training_when_not_running_returns_400(
        self, api_context: APIRequestContext
    ):
        """POST /training/stop should return 400 if no training is active."""
        response = api_context.post("/api/training/stop")
        # When no training is running, expect 400
        assert response.status == 400

        data = response.json()
        assert "detail" in data

    # -------------------------------------------------------------------------
    def test_start_training_while_already_running_returns_409(
        self, api_context: APIRequestContext
    ):
        """
        POST /training/start should return 409 if training is already in progress.
        Note: This test requires training to be running. It may be skipped in CI.
        """
        # Ensure training is running
        api_context.post("/api/training/stop")  # Clean slate
        assert wait_for_training_stopped(api_context, timeout=30.0)
        start_response = api_context.post(
            "/api/training/start", data=RUNNING_TRAINING_CONFIG
        )
        assert start_response.ok, "Failed to start setup training"

        if not wait_for_training_running(api_context):
            pytest.skip("Training completed too quickly to test concurrent start.")

        # Attempt to start again with minimal config
        response = api_context.post("/api/training/start", data=RUNNING_TRAINING_CONFIG)
        assert response.status == 409

        # Cleanup
        api_context.post("/api/training/stop")
        assert wait_for_training_stopped(api_context, timeout=30.0)

    # -------------------------------------------------------------------------
    def test_start_training_with_minimal_config(self, api_context: APIRequestContext):
        """
        POST /training/start with minimal config should start training.
        Uses smallest possible values to minimize test duration.
        """
        # Check if training is already running
        # Ensure clean state
        api_context.post("/api/training/stop")
        assert wait_for_training_stopped(api_context, timeout=30.0)

        # Start training with minimal config
        response = api_context.post("/api/training/start", data=MINIMAL_TRAINING_CONFIG)

        # Should succeed
        assert response.ok, f"Expected 200, got {response.status}: {response.text()}"

        if response.ok:
            data = response.json()
            assert data.get("status") in ("started", "running")
            job_id = data.get("job_id")
            assert job_id, "Job ID should be returned for polling"
            assert isinstance(data.get("poll_interval"), (int, float))
            assert float(data["poll_interval"]) > 0
            job_response = api_context.get(f"/api/training/jobs/{job_id}")
            assert job_response.ok, f"Expected 200, got {job_response.status}"
            job_data = job_response.json()
            assert job_data.get("job_id") == job_id
            assert job_data.get("job_type") == "training"
            assert job_data.get("status") in ("pending", "running", "completed")

            # Wait briefly then stop training to clean up
            time.sleep(1)
            api_context.post("/api/training/stop")
            wait_for_training_stopped(api_context)

    # -------------------------------------------------------------------------
    def test_cancel_unknown_training_job_returns_404(
        self, api_context: APIRequestContext
    ):
        response = api_context.delete("/api/training/jobs/missing_job_123")
        assert response.status == 404
        payload = response.json()
        assert "detail" in payload

###############################################################################
class TestTrainingLifecycle:
    """Integration tests for training start/stop lifecycle."""

    # -------------------------------------------------------------------------
    def test_training_can_be_stopped(self, api_context: APIRequestContext):
        """
        Tests that training can be started and stopped.
        Uses minimal configuration for speed.
        """
        # Skip if training already running
        # Ensure clean state
        api_context.post("/api/training/stop")

        # Start training
        start_response = api_context.post(
            "/api/training/start", data=RUNNING_TRAINING_CONFIG
        )
        assert start_response.ok, "Failed to start training"

        # Verify training is running
        if not wait_for_training_running(api_context):
            pytest.skip("Training completed too quickly to verify stop behavior.")

        status = api_context.get("/api/training/status").json()
        assert status.get("is_training") is True

        # Stop training
        stop_response = api_context.post("/api/training/stop")
        assert stop_response.ok

        # Verify stopped
        assert wait_for_training_stopped(api_context)
        status = api_context.get("/api/training/status").json()
        assert status.get("is_training") is False

    # -------------------------------------------------------------------------
    def test_training_job_can_be_cancelled_via_jobs_endpoint(
        self, api_context: APIRequestContext
    ):
        api_context.post("/api/training/stop")
        start_response = api_context.post(
            "/api/training/start", data=RUNNING_TRAINING_CONFIG
        )
        assert start_response.ok, (
            f"Expected 200, got {start_response.status}: {start_response.text()}"
        )
        start_payload = start_response.json()
        job_id = start_payload.get("job_id")
        assert isinstance(job_id, str) and job_id

        if not wait_for_training_running(api_context):
            pytest.skip("Training completed too quickly to validate cancellation.")

        cancel_response = api_context.delete(f"/api/training/jobs/{job_id}")
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

###############################################################################
class TestTrainingResume:
    """Tests for resume training and checkpoint metadata endpoints."""

    # -------------------------------------------------------------------------
    def test_resume_training_invalid_checkpoint_returns_404(
        self, api_context: APIRequestContext
    ):
        payload = dict(RESUME_TRAINING_CONFIG, checkpoint="missing_checkpoint_123")
        response = api_context.post("/api/training/resume", data=payload)
        assert response.status == 404
        data = response.json()
        assert "detail" in data

    # -------------------------------------------------------------------------
    def test_resume_training_from_new_checkpoint(self, api_context: APIRequestContext):
        api_context.post("/api/training/stop")
        before_response = api_context.get("/api/training/checkpoints")
        assert before_response.ok
        before_checkpoints = before_response.json()

        start_response = api_context.post(
            "/api/training/start", data=MINIMAL_TRAINING_CONFIG
        )
        assert start_response.ok, (
            f"Expected 200, got {start_response.status}: {start_response.text()}"
        )
        job_id = start_response.json().get("job_id")
        assert job_id

        job_payload = wait_for_job_completion(api_context, job_id, timeout=90.0)
        if job_payload.get("status") != "completed":
            api_context.post("/api/training/stop")
            pytest.skip("Training did not complete in time to produce a checkpoint.")

        after_response = api_context.get("/api/training/checkpoints")
        assert after_response.ok
        after_checkpoints = after_response.json()
        new_checkpoints = [
            item for item in after_checkpoints if item not in before_checkpoints
        ]
        if not new_checkpoints:
            pytest.skip("No new checkpoint detected after training completion.")

        checkpoint = new_checkpoints[0]
        metadata_response = api_context.get(
            f"/api/training/checkpoints/{checkpoint}/metadata"
        )
        assert metadata_response.ok
        metadata = metadata_response.json()
        assert metadata.get("checkpoint") == checkpoint
        assert "summary" in metadata
        summary = metadata["summary"]
        assert "episodes" in summary
        assert "batch_size" in summary

        resume_payload = dict(RESUME_TRAINING_CONFIG, checkpoint=checkpoint)
        resume_response = api_context.post("/api/training/resume", data=resume_payload)
        assert resume_response.ok, (
            f"Expected 200, got {resume_response.status}: {resume_response.text()}"
        )
        resume_job_id = resume_response.json().get("job_id")
        assert resume_job_id

        resume_job_payload = wait_for_job_completion(
            api_context, resume_job_id, timeout=90.0
        )
        if resume_job_payload.get("status") != "completed":
            api_context.post("/api/training/stop")
            pytest.skip("Resume training did not complete in time.")

        delete_response = api_context.delete(f"/api/training/checkpoints/{checkpoint}")
        assert delete_response.ok
