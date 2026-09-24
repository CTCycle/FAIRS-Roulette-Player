from __future__ import annotations

from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from server.api.settings import router as settings_router
from server.configurations.management import ConfigurationManager
from server.contracts.configuration import DeviceSettings, JobsSettings
from server.services.settings import SettingsService

###############################################################################
class TrainingSpy:

    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        self.jobs = JobsSettings(polling_interval=1.0)
        self.device = DeviceSettings(jit_compile=False, jit_backend="eager")

    # -------------------------------------------------------------------------
    def get_runtime_settings(self) -> tuple[JobsSettings, DeviceSettings]:
        return self.jobs, self.device

    # -------------------------------------------------------------------------
    def apply_runtime_settings(
        self,
        jobs: JobsSettings,
        device: DeviceSettings,
    ) -> None:
        self.jobs = jobs
        self.device = device

###############################################################################
def _build_client(tmp_path: Path) -> tuple[TestClient, ConfigurationManager]:
    manager = ConfigurationManager(runtime_path=tmp_path / "runtime-settings.json")
    service = SettingsService(manager, TrainingSpy())
    application = FastAPI()
    application.state.settings_service = service
    application.include_router(settings_router, prefix="/api")
    return TestClient(application), manager

###############################################################################
def test_settings_api_returns_only_structured_settings(tmp_path: Path) -> None:
    with _build_client(tmp_path)[0] as client:
        response = client.get("/api/settings")

    assert response.status_code == 200
    assert response.json() == {
        "jobs": {"polling_interval": 1.0},
        "device": {"jit_compile": False, "jit_backend": "eager"},
        "roulette": {
            "minimum_number": 0,
            "maximum_number": 36,
            "exclude_zero": False,
            "invert_colors": False,
            "show_number_labels": True,
        },
    }

###############################################################################
def test_settings_api_supports_partial_update_and_reload(tmp_path: Path) -> None:
    client, manager = _build_client(tmp_path)
    with client:
        jobs_response = client.patch(
            "/api/settings",
            json={"jobs": {"polling_interval": 2.5}},
        )
        device_response = client.patch(
            "/api/settings",
            json={"device": {"jit_compile": False, "jit_backend": "eager"}},
        )
        current_response = client.get("/api/settings")

    assert jobs_response.status_code == 200
    assert device_response.status_code == 200
    assert current_response.json() == {
        "jobs": {"polling_interval": 2.5},
        "device": {"jit_compile": False, "jit_backend": "eager"},
        "roulette": {
            "minimum_number": 0,
            "maximum_number": 36,
            "exclude_zero": False,
            "invert_colors": False,
            "show_number_labels": True,
        },
    }
    assert manager.get_json_settings().device.jit_backend == "eager"

    reloaded = ConfigurationManager(runtime_path=manager.runtime_path)
    assert reloaded.get_json_settings().jobs.polling_interval == 2.5

###############################################################################
def test_settings_api_accepts_jit_on_supported_python_runtime(tmp_path: Path) -> None:
    client, manager = _build_client(tmp_path)
    with client:
        response = client.patch(
            "/api/settings",
            json={"device": {"jit_compile": True, "jit_backend": "eager"}},
        )
        current = client.get("/api/settings")

    assert response.status_code == 200
    assert current.json()["device"] == {
        "jit_compile": True,
        "jit_backend": "eager",
    }
    assert manager.get_json_settings().device.jit_compile is True

###############################################################################
@pytest.mark.skipif(sys.platform != "win32", reason="Windows backend capability")
def test_settings_api_rejects_windows_inductor_while_jit_is_enabled(
    tmp_path: Path,
) -> None:
    client, manager = _build_client(tmp_path)
    with client:
        enabled = client.patch(
            "/api/settings",
            json={"device": {"jit_compile": True, "jit_backend": "eager"}},
        )
        rejected = client.patch(
            "/api/settings",
            json={"device": {"jit_compile": True, "jit_backend": "inductor"}},
        )
        current = client.get("/api/settings")

    assert enabled.status_code == 200
    assert rejected.status_code == 422
    assert "Triton" in rejected.json()["detail"]
    assert current.json()["device"] == {
        "jit_compile": True,
        "jit_backend": "eager",
    }
    assert manager.get_json_settings().device.jit_backend == "eager"

###############################################################################
def test_settings_api_rejects_unknown_and_invalid_values(tmp_path: Path) -> None:
    with _build_client(tmp_path)[0] as client:
        unknown = client.patch("/api/settings", json={"database": {"host": "x"}})
        low = client.patch("/api/settings", json={"jobs": {"polling_interval": 0.01}})
        blank = client.patch("/api/settings", json={"device": {"jit_backend": " "}})
        unknown_backend = client.patch(
            "/api/settings", json={"device": {"jit_backend": "unknown"}}
        )

    assert unknown.status_code == 422
    assert low.status_code == 422
    assert blank.status_code == 422
    assert unknown_backend.status_code == 422

###############################################################################
def test_settings_api_reset_restores_defaults(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    with client:
        client.patch(
            "/api/settings",
            json={"jobs": {"polling_interval": 4.0}},
        )
        response = client.post("/api/settings/reset")

    assert response.status_code == 200
    assert response.json() == {
        "jobs": {"polling_interval": 1.0},
        "device": {"jit_compile": False, "jit_backend": "eager"},
        "roulette": {
            "minimum_number": 0,
            "maximum_number": 36,
            "exclude_zero": False,
            "invert_colors": False,
            "show_number_labels": True,
        },
    }
