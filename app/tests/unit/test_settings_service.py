from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from server.configurations.management import ConfigurationManager
from server.contracts.configuration import DeviceSettings, JobsSettings
from server.contracts.settings import SettingsPatchRequest
from server.services.settings import SettingsPersistenceError, SettingsService

###############################################################################
class FakeTrainingService:

    def __init__(self) -> None:
        self.jobs = JobsSettings(polling_interval=1.0)
        self.device = DeviceSettings(jit_compile=False, jit_backend="inductor")
        self.calls: list[tuple[JobsSettings, DeviceSettings]] = []
        self.fail_next_apply = False

    # -------------------------------------------------------------------------
    def get_runtime_settings(self) -> tuple[JobsSettings, DeviceSettings]:
        return self.jobs, self.device

    # -------------------------------------------------------------------------
    def apply_runtime_settings(
        self,
        jobs: JobsSettings,
        device: DeviceSettings,
    ) -> None:
        self.calls.append((jobs, device))
        if self.fail_next_apply:
            self.fail_next_apply = False
            raise RuntimeError("simulated propagation failure")
        self.jobs = jobs
        self.device = device

###############################################################################
def _build_service(tmp_path: Path) -> tuple[SettingsService, FakeTrainingService, Path]:
    runtime_path = tmp_path / "runtime-settings.json"
    manager = ConfigurationManager(runtime_path=runtime_path)
    training_service = FakeTrainingService()
    return SettingsService(manager, training_service), training_service, runtime_path

###############################################################################
def test_get_and_partial_update_are_structured_only(tmp_path: Path) -> None:
    service, training_service, runtime_path = _build_service(tmp_path)

    response = service.get_settings()
    assert response.model_dump() == {
        "jobs": {"polling_interval": 1.0},
        "device": {"jit_compile": False, "jit_backend": "inductor"},
        "roulette": {
            "minimum_number": 0,
            "maximum_number": 36,
            "exclude_zero": False,
            "invert_colors": False,
            "show_number_labels": True,
        },
    }

    updated = service.update_settings(
        SettingsPatchRequest(jobs={"polling_interval": 2.5})
    )

    assert updated.jobs.polling_interval == 2.5
    assert updated.device.jit_compile is False
    assert updated.roulette.maximum_number == 36
    assert training_service.jobs.polling_interval == 2.5
    assert training_service.device.jit_backend == "inductor"
    assert json.loads(runtime_path.read_text(encoding="utf-8"))["jobs"] == {
        "polling_interval": 2.5
    }

###############################################################################
def test_roulette_update_persists_and_round_trips(tmp_path: Path) -> None:
    service, _, runtime_path = _build_service(tmp_path)

    updated = service.update_settings(
        SettingsPatchRequest(
            roulette={
                "minimum_number": 5,
                "maximum_number": 30,
                "exclude_zero": True,
                "invert_colors": True,
                "show_number_labels": False,
            }
        )
    )

    assert updated.roulette.minimum_number == 5
    assert updated.roulette.maximum_number == 30
    assert updated.roulette.exclude_zero is True
    assert updated.roulette.invert_colors is True
    assert updated.roulette.show_number_labels is False
    persisted = json.loads(runtime_path.read_text(encoding="utf-8"))
    assert persisted["roulette"] == {
        "minimum_number": 5,
        "maximum_number": 30,
        "exclude_zero": True,
        "invert_colors": True,
        "show_number_labels": False,
    }

    reloaded = SettingsService(
        ConfigurationManager(runtime_path=runtime_path),
        FakeTrainingService(),
    ).get_settings()
    assert reloaded.roulette == updated.roulette

###############################################################################
def test_partial_roulette_patch_is_validated_against_saved_range(tmp_path: Path) -> None:
    service, _, _ = _build_service(tmp_path)
    service.update_settings(
        SettingsPatchRequest(
            roulette={"minimum_number": 10, "maximum_number": 20},
        )
    )

    with pytest.raises(ValidationError, match="minimum_number"):
        service.update_settings(
            SettingsPatchRequest(roulette={"maximum_number": 5})
        )

    current = service.get_settings().roulette
    assert current.minimum_number == 10
    assert current.maximum_number == 20

###############################################################################
def test_device_update_preserves_backend_when_jit_is_disabled(tmp_path: Path) -> None:
    service, training_service, _ = _build_service(tmp_path)

    service.update_settings(
        SettingsPatchRequest(
            device={"jit_compile": True, "jit_backend": " eager "},
        )
    )
    updated = service.update_settings(SettingsPatchRequest(device={"jit_compile": False}))

    assert updated.device.jit_compile is False
    assert updated.device.jit_backend == "eager"
    assert training_service.device.jit_backend == "eager"

###############################################################################
def test_reset_uses_backend_defaults(tmp_path: Path) -> None:
    service, training_service, _ = _build_service(tmp_path)
    service.update_settings(
        SettingsPatchRequest(
            jobs={"polling_interval": 4.0},
            device={"jit_compile": True, "jit_backend": "eager"},
            roulette={
                "minimum_number": 3,
                "maximum_number": 21,
                "exclude_zero": True,
                "invert_colors": True,
                "show_number_labels": False,
            },
        )
    )

    response = service.reset_settings()

    assert response.jobs.polling_interval == 1.0
    assert response.device.jit_compile is False
    assert response.device.jit_backend == "inductor"
    assert response.roulette.minimum_number == 0
    assert response.roulette.maximum_number == 36
    assert response.roulette.exclude_zero is False
    assert response.roulette.invert_colors is False
    assert response.roulette.show_number_labels is True
    assert training_service.jobs.polling_interval == 1.0

###############################################################################
def test_propagation_failure_restores_persisted_and_training_state(
    tmp_path: Path,
) -> None:
    service, training_service, runtime_path = _build_service(tmp_path)
    training_service.fail_next_apply = True

    with pytest.raises(SettingsPersistenceError, match="Unable to save settings"):
        service.update_settings(SettingsPatchRequest(jobs={"polling_interval": 3.0}))

    assert service.get_settings().jobs.polling_interval == 1.0
    assert json.loads(runtime_path.read_text(encoding="utf-8"))["jobs"] == {
        "polling_interval": 1.0
    }
    assert training_service.jobs.polling_interval == 1.0
    assert len(training_service.calls) == 2

###############################################################################
def test_invalid_patch_is_rejected_before_service_update() -> None:
    with pytest.raises(ValidationError):
        SettingsPatchRequest(jobs={"polling_interval": 0.01})
    with pytest.raises(ValidationError):
        SettingsPatchRequest(device={"jit_backend": "   "})
    with pytest.raises(ValidationError):
        SettingsPatchRequest(
            roulette={"minimum_number": 20, "maximum_number": 10}
        )
    with pytest.raises(ValidationError):
        SettingsPatchRequest.model_validate({"database": {"host": "secret"}})

###############################################################################
def test_persistence_failure_does_not_publish_new_cache_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, training_service, runtime_path = _build_service(tmp_path)
    manager = service._manager()  # noqa: SLF001
    previous = manager.get_json_settings()
    monkeypatch.setattr(
        manager,
        "_persist_json_settings",
        Mock(side_effect=RuntimeError("disk full")),
    )

    with pytest.raises(RuntimeError, match="disk full"):
        service.update_settings(SettingsPatchRequest(jobs={"polling_interval": 2.0}))

    assert manager.get_json_settings() == previous
    assert training_service.jobs.polling_interval == 1.0
    assert json.loads(runtime_path.read_text(encoding="utf-8"))["jobs"] == {
        "polling_interval": 1.0
    }
