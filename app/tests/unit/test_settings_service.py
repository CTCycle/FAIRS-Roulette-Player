# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from server.contracts.configuration import DatabaseSettings, DeviceSettings, JobsSettings
from server.contracts.settings import SettingsPatchRequest
from server.repositories.application_settings import ApplicationSettingsRepository
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import initialize_database
from server.repositories.database.runtime import RuntimeDatabaseManager
from server.services import settings as settings_module
from server.services.settings import SettingsPersistenceError, SettingsService


class FakeTrainingService:
    def __init__(self) -> None:
        self.jobs = JobsSettings(polling_interval=1.0)
        self.device = DeviceSettings(jit_compile=False, jit_backend="eager")
        self.roulette = None
        self.calls: list[tuple[JobsSettings, DeviceSettings]] = []
        self.fail_next_apply = False

    def get_runtime_settings(self) -> tuple[JobsSettings, DeviceSettings]:
        return self.jobs, self.device

    def apply_runtime_settings(
        self, jobs: JobsSettings, device: DeviceSettings
    ) -> None:
        self.calls.append((jobs, device))
        if self.fail_next_apply:
            self.fail_next_apply = False
            raise RuntimeError("simulated propagation failure")
        self.jobs = jobs
        self.device = device

    def apply_roulette_settings(self, settings) -> None:
        self.roulette = settings


def _sqlite_settings() -> DatabaseSettings:
    return DatabaseSettings(
        embedded_database=True,
        engine=None,
        host=None,
        port=None,
        database_name=None,
        username=None,
        password=None,
        ssl=False,
        ssl_ca=None,
        connect_timeout=10,
        insert_batch_size=1000,
    )


def _build_service(tmp_path: Path):
    database_path = tmp_path / "preferences.db"
    settings = _sqlite_settings()
    initialize_database(settings, database_path=database_path)
    database = FAIRSDatabase(settings, database_path=database_path)
    ApplicationSettingsRepository().ensure_row(database)
    runtime_database = RuntimeDatabaseManager(database)
    training_service = FakeTrainingService()
    return SettingsService(runtime_database, training_service), training_service, runtime_database, database_path


def test_get_and_partial_update_persist_in_active_database(tmp_path: Path) -> None:
    service, training_service, runtime_database, database_path = _build_service(tmp_path)

    response = service.get_settings()
    assert response.model_dump() == {
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

    updated = service.update_settings(SettingsPatchRequest(jobs={"polling_interval": 2.5}))

    assert updated.jobs.polling_interval == 2.5
    assert training_service.jobs.polling_interval == 2.5
    persisted = ApplicationSettingsRepository().get(runtime_database)
    assert persisted.jobs.polling_interval == 2.5
    assert not (tmp_path / "runtime-settings.json").exists()
    assert database_path.exists()


def test_settings_survive_database_reopen(tmp_path: Path) -> None:
    service, _, _, database_path = _build_service(tmp_path)
    updated = service.update_settings(SettingsPatchRequest(roulette={"invert_colors": True}))
    assert updated.roulette.invert_colors is True

    settings = _sqlite_settings()
    reopened = FAIRSDatabase(settings, database_path=database_path)
    reloaded = SettingsService(RuntimeDatabaseManager(reopened), FakeTrainingService())
    assert reloaded.get_settings().roulette.invert_colors is True


def test_validated_database_row_removes_legacy_settings_file(tmp_path: Path) -> None:
    settings = _sqlite_settings()
    database_path = tmp_path / "authoritative.db"
    initialize_database(settings, database_path=database_path)
    database = FAIRSDatabase(settings, database_path=database_path)
    repository = ApplicationSettingsRepository()
    repository.ensure_row(database)
    legacy_path = tmp_path / "runtime-settings.json"
    legacy_path.write_text(json.dumps({"jobs": {"polling_interval": 8.0}}), encoding="utf-8")
    try:
        current = repository.ensure_row(
            database,
            legacy_path=legacy_path,
            allow_legacy_import=True,
        )

        assert current.jobs.polling_interval == 1.0
        assert not legacy_path.exists()
    finally:
        database.dispose()


def test_partial_roulette_patch_is_validated_against_saved_range(tmp_path: Path) -> None:
    service, _, _, _ = _build_service(tmp_path)
    service.update_settings(SettingsPatchRequest(roulette={"minimum_number": 10, "maximum_number": 20}))

    with pytest.raises(ValidationError, match="minimum_number"):
        service.update_settings(SettingsPatchRequest(roulette={"maximum_number": 5}))
    current = service.get_settings().roulette
    assert current.minimum_number == 10
    assert current.maximum_number == 20


def test_device_update_preserves_backend_when_jit_is_disabled(tmp_path: Path) -> None:
    service, training_service, _, _ = _build_service(tmp_path)
    service.update_settings(SettingsPatchRequest(device={"jit_compile": False, "jit_backend": " eager "}))
    updated = service.update_settings(SettingsPatchRequest(device={"jit_compile": False}))

    assert updated.device.jit_compile is False
    assert updated.device.jit_backend == "eager"
    assert training_service.device.jit_backend == "eager"


def test_reset_uses_backend_defaults(tmp_path: Path) -> None:
    service, training_service, _, _ = _build_service(tmp_path)
    service.update_settings(
        SettingsPatchRequest(
            jobs={"polling_interval": 4.0},
            device={"jit_compile": False, "jit_backend": "eager"},
            roulette={"minimum_number": 3, "maximum_number": 21, "exclude_zero": True},
        )
    )

    response = service.reset_settings()
    assert response.jobs.polling_interval == 1.0
    assert response.roulette.minimum_number == 0
    assert response.roulette.maximum_number == 36
    assert response.roulette.exclude_zero is False
    assert training_service.jobs.polling_interval == 1.0


def test_enabling_jit_runs_runtime_preflight_before_database_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, training_service, runtime_database, _ = _build_service(tmp_path)
    validator = Mock(side_effect=ValueError("JIT runtime unavailable"))
    monkeypatch.setattr(settings_module, "validate_jit_runtime", validator)

    with pytest.raises(ValueError, match="JIT runtime unavailable"):
        service.update_settings(SettingsPatchRequest(device={"jit_compile": True, "jit_backend": "eager"}))

    validator.assert_called_once_with(True, "eager")
    assert service.get_settings().device.jit_compile is False
    assert training_service.device.jit_compile is False
    assert ApplicationSettingsRepository().get(runtime_database).device.jit_compile is False


def test_propagation_failure_restores_database_and_training_state(tmp_path: Path) -> None:
    service, training_service, runtime_database, _ = _build_service(tmp_path)
    training_service.fail_next_apply = True

    with pytest.raises(SettingsPersistenceError, match="Unable to save settings"):
        service.update_settings(SettingsPatchRequest(jobs={"polling_interval": 3.0}))

    assert service.get_settings().jobs.polling_interval == 1.0
    assert ApplicationSettingsRepository().get(runtime_database).jobs.polling_interval == 1.0
    assert training_service.jobs.polling_interval == 1.0
    assert len(training_service.calls) == 2


def test_invalid_patch_is_rejected_before_service_update() -> None:
    with pytest.raises(ValidationError):
        SettingsPatchRequest(jobs={"polling_interval": 0.01})
    with pytest.raises(ValidationError):
        SettingsPatchRequest(device={"jit_backend": "   "})
    with pytest.raises(ValidationError):
        SettingsPatchRequest(roulette={"minimum_number": 20, "maximum_number": 10})
    with pytest.raises(ValidationError):
        SettingsPatchRequest.model_validate({"database": {"host": "secret"}})


def test_database_write_failure_does_not_publish_new_training_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, training_service, _, _ = _build_service(tmp_path)
    previous = service.get_settings()
    monkeypatch.setattr(
        service.repository,
        "replace",
        Mock(side_effect=RuntimeError("database write failed")),
    )

    with pytest.raises(RuntimeError, match="database write failed"):
        service.update_settings(SettingsPatchRequest(jobs={"polling_interval": 2.0}))

    assert service.get_settings() == previous
    assert training_service.jobs.polling_interval == 1.0
