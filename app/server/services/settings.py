# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

from threading import RLock
from typing import TYPE_CHECKING

from server.common.utils.logger import logger
from server.common.runtime_capabilities import validate_jit_runtime
from server.contracts.configuration import (
    DeviceSettings,
    JobsSettings,
    JsonServerSettings,
)
from server.contracts.settings import SettingsPatchRequest, SettingsResponse
from server.repositories.application_settings import ApplicationSettingsRepository
from server.repositories.database.runtime import RuntimeDatabaseManager

if TYPE_CHECKING:
    from server.services.training import TrainingService


###############################################################################
class SettingsPersistenceError(RuntimeError):
    """Raised when runtime settings cannot be safely published or restored."""


###############################################################################
class SettingsService:

    # -------------------------------------------------------------------------
    def __init__(
        self,
        database: RuntimeDatabaseManager,
        training_service: TrainingService,
    ) -> None:
        self.database = database
        self.repository = ApplicationSettingsRepository()
        self.training_service = training_service
        self._lock = RLock()

    # -------------------------------------------------------------------------
    @staticmethod
    def _response(settings: JsonServerSettings) -> SettingsResponse:
        return SettingsResponse.from_json_settings(settings)

    # -------------------------------------------------------------------------
    def get_settings(self) -> SettingsResponse:
        return self._response(self.repository.get(self.database))

    # -------------------------------------------------------------------------
    @staticmethod
    def _merge_patch(
        current: JsonServerSettings,
        patch: SettingsPatchRequest,
    ) -> JsonServerSettings:
        payload = current.model_dump(mode="python")
        patch_payload = patch.model_dump(
            mode="python",
            exclude_unset=True,
            exclude_none=False,
        )
        for block_name in ("jobs", "device", "roulette"):
            block_patch = patch_payload.get(block_name)
            if isinstance(block_patch, dict):
                payload[block_name].update(block_patch)
        return JsonServerSettings.model_validate(payload)

    # -------------------------------------------------------------------------
    def _restore_after_propagation_failure(
        self,
        previous_json: JsonServerSettings,
        previous_training: tuple[JobsSettings, DeviceSettings],
        cause: Exception,
    ) -> None:
        try:
            self.repository.replace(self.database, previous_json)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to restore runtime settings after propagation failure"
            )
        try:
            self.training_service.apply_runtime_settings(*previous_training)
            self.training_service.apply_roulette_settings(
                previous_json.roulette.to_runtime_settings()
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to restore training runtime settings")
        raise SettingsPersistenceError("Unable to save settings.") from cause

    # -------------------------------------------------------------------------
    def _persist_and_apply(
        self,
        previous_json: JsonServerSettings,
        candidate: JsonServerSettings,
    ) -> SettingsResponse:
        previous_training = self.training_service.get_runtime_settings()
        if candidate.device.jit_compile:
            validate_jit_runtime(
                candidate.device.jit_compile,
                candidate.device.jit_backend,
            )
        self.repository.replace(self.database, candidate)
        try:
            self.training_service.apply_runtime_settings(
                candidate.jobs,
                candidate.device,
            )
            self.training_service.apply_roulette_settings(
                candidate.roulette.to_runtime_settings()
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to publish runtime settings to TrainingService")
            self._restore_after_propagation_failure(
                previous_json,
                previous_training,
                exc,
            )
        return self._response(candidate)

    # -------------------------------------------------------------------------
    def update_settings(self, patch: SettingsPatchRequest) -> SettingsResponse:
        with self._lock:
            previous = self.repository.get(self.database)
            candidate = self._merge_patch(previous, patch)
            return self._persist_and_apply(previous, candidate)

    # -------------------------------------------------------------------------
    def reset_settings(self) -> SettingsResponse:
        with self._lock:
            previous = self.repository.get(self.database)
            return self._persist_and_apply(previous, JsonServerSettings())
