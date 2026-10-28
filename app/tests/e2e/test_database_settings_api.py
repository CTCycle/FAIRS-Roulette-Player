# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import sys
import pytest
from playwright.sync_api import APIRequestContext
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.api.settings import router as settings_router
from server.contracts.configuration import DatabaseSettings, DeviceSettings, JobsSettings, RouletteSettings
from server.repositories.application_settings import ApplicationSettingsRepository
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import initialize_database
from server.repositories.database.runtime import RuntimeDatabaseManager
from server.services.settings import SettingsService

"""
E2E tests for dataset listing APIs under /datasets/training.
"""



DATASET_NAME = "e2e_dataset_for_listing"


###############################################################################
def ensure_dataset_for_listing(api_context: APIRequestContext) -> None:
    summary_response = api_context.get("/api/datasets/training/summary")
    assert summary_response.ok
    summary_payload = summary_response.json()
    datasets = summary_payload.get("datasets", [])
    existing = next(
        (item for item in datasets if item.get("dataset_name") == DATASET_NAME),
        None,
    )
    if existing is not None:
        return

    csv_content = b"idx,outcome\n0,0\n1,14\n2,28\n3,7\n4,22"
    upload_response = api_context.post(
        "/api/data/upload?dataset_kind=training&csv_separator=%2C",
        multipart={
            "file": {
                "name": f"{DATASET_NAME}.csv",
                "mimeType": "text/csv",
                "buffer": csv_content,
            }
        },
    )
    assert upload_response.ok, (
        f"Expected 200, got {upload_response.status}: {upload_response.text()}"
    )


###############################################################################
class TestRouletteDatasetsEndpoints:
    """Tests for /datasets/training endpoints."""

    # -------------------------------------------------------------------------
    def test_list_roulette_datasets(self, api_context: APIRequestContext):
        ensure_dataset_for_listing(api_context)
        response = api_context.get("/api/datasets/training")
        assert response.ok, f"Expected 200, got {response.status}"

        data = response.json()
        assert "datasets" in data
        assert isinstance(data["datasets"], list)
        assert data["datasets"], "Expected at least one dataset after setup."
        sample = data["datasets"][0]
        assert "dataset_id" in sample
        assert "dataset_name" in sample
        assert isinstance(sample["dataset_id"], int)
        assert isinstance(sample["dataset_name"], str)
        assert sample["dataset_name"]

    # -------------------------------------------------------------------------
    def test_list_roulette_datasets_summary(self, api_context: APIRequestContext):
        ensure_dataset_for_listing(api_context)
        response = api_context.get("/api/datasets/training/summary")
        assert response.ok, f"Expected 200, got {response.status}"

        data = response.json()
        assert "datasets" in data
        assert isinstance(data["datasets"], list)
        assert data["datasets"], "Expected at least one dataset after setup."
        sample = data["datasets"][0]
        assert "dataset_id" in sample
        assert "dataset_name" in sample
        assert "row_count" in sample
        assert isinstance(sample["dataset_id"], int)
        assert isinstance(sample["row_count"], int)
        assert sample["row_count"] >= 0


###############################################################################
class TrainingSpy:

    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        self.jobs = JobsSettings(polling_interval=1.0)
        self.device = DeviceSettings(jit_compile=False, jit_backend="eager")
        self.roulette: RouletteSettings | None = None

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

    # -------------------------------------------------------------------------
    def apply_roulette_settings(self, settings: RouletteSettings) -> None:
        self.roulette = settings


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


###############################################################################
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
            json={"device": {"jit_compile": True, "jit_backend": "eager"}},
        )
        roulette_response = client.patch(
            "/api/settings",
            json={
                "roulette": {
                    "minimum_number": 1,
                    "maximum_number": 12,
                    "exclude_zero": True,
                    "invert_colors": True,
                    "show_number_labels": False,
                }
            },
        )
        current_response = client.get("/api/settings")

    assert jobs_response.status_code == 200
    assert device_response.status_code == 200
    assert roulette_response.status_code == 200
    assert current_response.json() == {
        "jobs": {"polling_interval": 2.5},
        "device": {"jit_compile": True, "jit_backend": "eager"},
        "roulette": {
            "minimum_number": 1,
            "maximum_number": 12,
            "exclude_zero": True,
            "invert_colors": True,
            "show_number_labels": False,
        },
    }
    persisted = ApplicationSettingsRepository().get(manager)
    assert persisted.device.jit_compile is True
    assert persisted.device.jit_backend == "eager"
    assert persisted.jobs.polling_interval == 2.5
    assert persisted.roulette.minimum_number == 1
    assert persisted.roulette.maximum_number == 12
    assert persisted.roulette.exclude_zero is True
    assert persisted.roulette.invert_colors is True
    assert persisted.roulette.show_number_labels is False


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
