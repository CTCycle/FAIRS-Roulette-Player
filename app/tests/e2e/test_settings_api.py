# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from server.api.settings import router as settings_router
from server.contracts.configuration import DatabaseSettings, DeviceSettings, JobsSettings
from server.repositories.application_settings import ApplicationSettingsRepository
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import initialize_database
from server.repositories.database.runtime import RuntimeDatabaseManager
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
def _sqlite_settings() -> DatabaseSettings:
    return DatabaseSettings(True, None, None, None, None, None, None, False, None, 10, 1000)

###############################################################################
def _build_client(tmp_path: Path) -> tuple[TestClient, RuntimeDatabaseManager]:
    database_path = tmp_path / "settings.db"
    initialize_database(_sqlite_settings(), database_path=database_path)
    database = FAIRSDatabase(_sqlite_settings(), database_path=database_path)
    ApplicationSettingsRepository().ensure_row(database)
    manager = RuntimeDatabaseManager(database)
    service = SettingsService(manager, TrainingSpy())
    application = FastAPI()
    application.state.settings_service = service
    application.include_router(settings_router, prefix="/api")
    return TestClient(application), manager


@contextmanager
def _client_session(tmp_path: Path) -> Iterator[tuple[TestClient, RuntimeDatabaseManager]]:
    client, manager = _build_client(tmp_path)
    try:
        with client:
            yield client, manager
    finally:
        manager.dispose()

###############################################################################
def test_settings_api_returns_only_structured_settings(tmp_path: Path) -> None:
    with _client_session(tmp_path) as (client, _manager):
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
    with _client_session(tmp_path) as (client, manager):
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
    persisted = ApplicationSettingsRepository().get(manager)
    assert persisted.device.jit_backend == "eager"
    assert persisted.jobs.polling_interval == 2.5

###############################################################################
def test_settings_api_accepts_jit_on_supported_python_runtime(tmp_path: Path) -> None:
    with _client_session(tmp_path) as (client, manager):
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
    assert ApplicationSettingsRepository().get(manager).device.jit_compile is True

###############################################################################
@pytest.mark.skipif(sys.platform != "win32", reason="Windows backend capability")
def test_settings_api_rejects_windows_inductor_while_jit_is_enabled(
    tmp_path: Path,
) -> None:
    with _client_session(tmp_path) as (client, manager):
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
    assert ApplicationSettingsRepository().get(manager).device.jit_backend == "eager"

###############################################################################
def test_settings_api_rejects_unknown_and_invalid_values(tmp_path: Path) -> None:
    with _client_session(tmp_path) as (client, _manager):
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
    with _client_session(tmp_path) as (client, _manager):
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
