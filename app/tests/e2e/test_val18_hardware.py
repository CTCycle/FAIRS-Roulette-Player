"""VAL-18 live CUDA, mixed-precision, and JIT training coverage."""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from uuid import uuid4

import pytest
import torch
from keras.mixed_precision import global_policy, set_global_policy
from playwright.sync_api import APIRequestContext

from server.learning.training.device import DeviceConfig


@pytest.mark.skipif(not torch.cuda.is_available(), reason="VAL-18 requires CUDA")
def test_cuda_mixed_precision_eager_jit_training_publishes_checkpoint(
    api_context: APIRequestContext,
) -> None:
    configured_data_dir = os.getenv("FAIRS_DATA_DIR", "").strip()
    if not configured_data_dir:
        pytest.skip("VAL-18 requires an isolated FAIRS_DATA_DIR")
    data_root = Path(configured_data_dir).expanduser().resolve()
    canonical_data_root = Path(__file__).resolve().parents[2] / "resources"
    if data_root == canonical_data_root.resolve():
        pytest.skip("VAL-18 must not mutate the canonical application data root")

    settings_response = api_context.get("/api/settings")
    assert settings_response.ok, settings_response.text()
    original_device_settings = settings_response.json()["device"]

    checkpoint = f"val18_cuda_{uuid4().hex[:10]}"
    configuration = {
        "episodes": 1,
        "max_steps_episode": 100,
        "perceptive_field_size": 8,
        "qnet_neurons": 8,
        "embedding_dimensions": 8,
        "batch_size": 100,
        "replay_buffer_size": 100,
        "max_memory_size": 100,
        "dataset_id": 5,
        "use_data_generator": False,
        "use_device_gpu": True,
        "device_id": 0,
        "use_mixed_precision": True,
        "checkpoint_name": checkpoint,
    }
    job_id: str | None = None

    try:
        jit_response = api_context.patch(
            "/api/settings",
            data={"device": {"jit_compile": True, "jit_backend": "eager"}},
        )
        assert jit_response.status == 200, jit_response.text()
        current_settings = api_context.get("/api/settings")
        assert current_settings.ok, current_settings.text()
        assert current_settings.json()["device"] == {
            "jit_compile": True,
            "jit_backend": "eager",
        }

        previous_policy = global_policy()
        previous_device = torch.cuda.current_device()
        try:
            selected_device = DeviceConfig(configuration).set_device()
            assert selected_device == torch.device("cuda:0")
            assert torch.cuda.current_device() == 0
            assert global_policy().name == "mixed_float16"
            with pytest.raises(RuntimeError, match="CUDA device_id is invalid: 1"):
                DeviceConfig({**configuration, "device_id": 1}).set_device()
            with pytest.raises(RuntimeError, match="Mixed precision requires GPU"):
                DeviceConfig(
                    {
                        **configuration,
                        "use_device_gpu": False,
                        "use_mixed_precision": True,
                    }
                ).set_device()
        finally:
            set_global_policy(previous_policy)
            torch.cuda.set_device(previous_device)

        start_response = api_context.post(
            "/api/training/start", data=configuration
        )
        assert start_response.status == 202, start_response.text()
        job_id = start_response.json().get("job_id")
        assert isinstance(job_id, str) and job_id

        deadline = time.monotonic() + 240.0
        job_payload: dict = {}
        while time.monotonic() < deadline:
            response = api_context.get(f"/api/training/jobs/{job_id}")
            assert response.ok, response.text()
            job_payload = response.json()
            if job_payload.get("status") in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.5)

        assert job_payload.get("status") == "completed", job_payload
        assert float(job_payload.get("progress", 0.0)) == pytest.approx(100.0)

        status_response = api_context.get("/api/training/status")
        assert status_response.ok, status_response.text()
        status = status_response.json()
        assert status["is_training"] is False, status
        assert status["job_id"] is None, status
        assert status["latest_stats"]["status"] == "completed", status
        for metric in ("loss", "rmse"):
            value = status["latest_stats"].get(metric)
            assert isinstance(value, (int, float)) and math.isfinite(float(value))

        metadata_response = api_context.get(
            f"/api/training/checkpoints/{checkpoint}/metadata"
        )
        assert metadata_response.ok, metadata_response.text()
        metadata = metadata_response.json()
        assert metadata["checkpoint"] == checkpoint
        assert metadata["summary"]["dataset_id"] == 5
        assert metadata["summary"]["episodes"] == 1
        checkpoint_root = data_root / "checkpoints" / checkpoint
        assert (checkpoint_root / ".complete").is_file()
        assert (checkpoint_root / "saved_model.keras").is_file()

        persisted_path = checkpoint_root / "configuration" / "configuration.json"
        persisted_training = json.loads(persisted_path.read_text(encoding="utf-8"))["training"]
        assert persisted_training["use_device_gpu"] is True
        assert persisted_training["device_id"] == 0
        assert persisted_training["use_mixed_precision"] is True

        log_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in (data_root / "logs").glob("FAIRS_*.log")
        )
        assert "GPU (cuda:0) is set as the active device." in log_text
        assert "Mixed precision policy is active during training" in log_text

        print(
            "VAL18_RESULT "
            f"job_id={job_id} checkpoint={checkpoint} "
            f"loss={status['latest_stats']['loss']} "
            f"rmse={status['latest_stats']['rmse']} "
            "device=cuda:0 mixed_precision=mixed_float16 jit=eager"
        )
    finally:
        api_context.post("/api/training/stop")
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            status_response = api_context.get("/api/training/status")
            if status_response.ok and not status_response.json().get("is_training"):
                break
            time.sleep(0.2)

        checkpoints_response = api_context.get("/api/training/checkpoints")
        if checkpoints_response.ok and checkpoint in checkpoints_response.json():
            delete_response = api_context.delete(
                f"/api/training/checkpoints/{checkpoint}"
            )
            assert delete_response.ok, delete_response.text()

        restore_response = api_context.patch(
            "/api/settings", data={"device": original_device_settings}
        )
        assert restore_response.status == 200, restore_response.text()
