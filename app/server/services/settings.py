from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import TYPE_CHECKING

from server.common.utils.logger import logger
from server.common.runtime_capabilities import validate_jit_runtime
from server.configurations.management import ConfigurationManager
from server.configurations.startup import get_configuration_manager
from server.contracts.configuration import DeviceSettings, JobsSettings, JsonServerSettings
from server.contracts.settings import SettingsPatchRequest, SettingsResponse

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
        configuration_manager: ConfigurationManager | None = None,
        training_service: TrainingService | None = None,
        *,
        configuration_manager_factory: Callable[[], ConfigurationManager]
        | None = None,
    ) -> None:
        if training_service is None:
            raise ValueError("SettingsService requires a TrainingService.")
        self._configuration_manager = configuration_manager
        self._configuration_manager_factory = (
            configuration_manager_factory or get_configuration_manager
        )
        self.training_service = training_service
        self._lock = RLock()

    # -------------------------------------------------------------------------
    def _manager(self) -> ConfigurationManager:
        if self._configuration_manager is None:
            self._configuration_manager = self._configuration_manager_factory()
        return self._configuration_manager

    # -------------------------------------------------------------------------
    @staticmethod
    def _response(settings: JsonServerSettings) -> SettingsResponse:
        return SettingsResponse.from_json_settings(settings)

    # -------------------------------------------------------------------------
    def get_settings(self) -> SettingsResponse:
        return self._response(self._manager().get_json_settings())

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
    def _training_snapshot(
        self,
        fallback_jobs: JobsSettings,
        fallback_device: DeviceSettings,
    ) -> tuple[JobsSettings, DeviceSettings]:
        snapshot = getattr(self.training_service, "get_runtime_settings", None)
        if callable(snapshot):
            return snapshot()
        return fallback_jobs, fallback_device

    # -------------------------------------------------------------------------
    def _restore_after_propagation_failure(
        self,
        previous_json: JsonServerSettings,
        previous_training: tuple[JobsSettings, DeviceSettings],
        cause: Exception,
    ) -> None:
        try:
            self._manager().replace_json_settings(previous_json)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to restore runtime settings after propagation failure")
        try:
            self.training_service.apply_runtime_settings(*previous_training)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to restore training runtime settings")
        raise SettingsPersistenceError("Unable to save settings.") from cause

    # -------------------------------------------------------------------------
    def _persist_and_apply(
        self,
        previous_json: JsonServerSettings,
        candidate: JsonServerSettings,
    ) -> SettingsResponse:
        previous_training = self._training_snapshot(
            JobsSettings(polling_interval=previous_json.jobs.polling_interval),
            DeviceSettings(
                jit_compile=previous_json.device.jit_compile,
                jit_backend=previous_json.device.jit_backend,
            ),
        )
        if candidate.device.jit_compile:
            validate_jit_runtime(
                candidate.device.jit_compile,
                candidate.device.jit_backend,
            )
        self._manager().replace_json_settings(candidate)
        try:
            self.training_service.apply_runtime_settings(
                candidate.jobs,
                candidate.device,
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
            previous = self._manager().get_json_settings()
            candidate = self._merge_patch(previous, patch)
            return self._persist_and_apply(previous, candidate)

    # -------------------------------------------------------------------------
    def reset_settings(self) -> SettingsResponse:
        with self._lock:
            previous = self._manager().get_json_settings()
            return self._persist_and_apply(previous, JsonServerSettings())
