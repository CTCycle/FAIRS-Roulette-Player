# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlalchemy import text

from server.configurations.database_config import (
    DatabaseConfigurationError,
    DatabaseConfigurationStore,
    LoadedDatabaseConfiguration,
)
from server.contracts.configuration import JsonServerSettings
from server.contracts.database_configuration import (
    DatabaseConfigurationInput,
    DatabaseStatusResponse,
    DatabaseTestResponse,
    database_settings_from_input,
)
from server.repositories.application_settings import ApplicationSettingsRepository
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import initialize_database
from server.repositories.database.runtime import (
    DatabaseSwitchConflict,
    RuntimeDatabaseManager,
)
from server.services.startup_validation import run_startup_validations


###############################################################################
class DatabaseSwitchError(RuntimeError):
    """A candidate database could not be safely activated."""


###############################################################################
class DatabaseConfigurationService:
    # -------------------------------------------------------------------------
    def __init__(
        self,
        *,
        store: DatabaseConfigurationStore,
        runtime_database: RuntimeDatabaseManager,
        application: Any,
        activate_services: Callable[
            [LoadedDatabaseConfiguration | None, JsonServerSettings | None], None
        ],
        settings_repository: ApplicationSettingsRepository | None = None,
    ) -> None:
        self.store = store
        self.runtime_database = runtime_database
        self.application = application
        self.activate_services = activate_services
        self.settings_repository = (
            settings_repository or ApplicationSettingsRepository()
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def _active_backend(runtime_database: RuntimeDatabaseManager) -> str | None:
        database = runtime_database.active
        if database is None:
            return None
        return "sqlite" if database.settings.embedded_database else "postgresql"

    # -------------------------------------------------------------------------
    def get_status(self) -> DatabaseStatusResponse:
        try:
            loaded = self.store.current()
            configuration = self.store.to_public(loaded)
            message = getattr(self.application.state, "recovery_message", None)
        except DatabaseConfigurationError as exc:
            configuration = None
            message = str(exc)
        lifecycle = getattr(self.application.state, "lifecycle", "recovery")
        switching = self.runtime_database.is_switching
        status = (
            "testing" if switching else "ready" if lifecycle == "ready" else "recovery"
        )
        active_backend = self._active_backend(self.runtime_database)
        return DatabaseStatusResponse(
            configuration=configuration,
            active_backend=active_backend,
            status=status,
            message=message,
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def _settings_and_path(candidate: DatabaseConfigurationInput, password: str | None):
        normalized = candidate.model_copy(
            update={
                "sqlite_path": (
                    str(Path(candidate.sqlite_path).expanduser().resolve())
                    if candidate.backend == "sqlite" and candidate.sqlite_path
                    else None
                ),
                "password": None,
                "clear_password": False,
            }
        )
        settings = database_settings_from_input(normalized, password)
        database_path = (
            Path(normalized.sqlite_path) if normalized.backend == "sqlite" else None
        )
        return normalized, settings, database_path

    # -------------------------------------------------------------------------
    def test_connection(
        self, candidate: DatabaseConfigurationInput
    ) -> DatabaseTestResponse:
        try:
            _, password = self.store.resolve_input(candidate)
            normalized, settings, database_path = self._settings_and_path(
                candidate, password
            )
            database = FAIRSDatabase(settings, database_path=database_path)
            try:
                with database.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
            finally:
                database.dispose()
        except Exception:  # noqa: BLE001
            backend = candidate.backend
            message = (
                "Unable to open the SQLite file. Check its path and file permissions."
                if backend == "sqlite"
                else "Unable to connect to PostgreSQL. Check the host, database, credentials, and SSL settings."
            )
            return DatabaseTestResponse(success=False, message=message)
        return DatabaseTestResponse(
            success=True,
            message=f"Connection to {normalized.backend} succeeded.",
        )

    # -------------------------------------------------------------------------
    def _reject_active_work(self) -> None:
        training = getattr(self.application.state, "training_run_manager", None)
        if training is not None and training.is_job_running():
            raise DatabaseSwitchConflict(
                "Stop the active training run before switching databases."
            )
        inference = getattr(self.application.state, "inference_service", None)
        if inference is not None and inference.state.has_sessions():
            raise DatabaseSwitchConflict(
                "Close active inference sessions before switching databases."
            )

    # -------------------------------------------------------------------------
    def activate(
        self,
        candidate: DatabaseConfigurationInput,
    ) -> DatabaseStatusResponse:
        normalized, password = self.store.resolve_input(candidate)
        normalized, settings, database_path = self._settings_and_path(
            normalized, password
        )
        candidate_database: FAIRSDatabase | None = None
        try:
            with self.runtime_database.switching():
                self._reject_active_work()
                # Migrations can change schema objects used by requests. Drain
                # the active database before inspecting or initializing a target
                # that may be the same physical database.
                initialize_database(settings, database_path=database_path)
                candidate_database = FAIRSDatabase(
                    settings, database_path=database_path
                )
                with candidate_database.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                application_settings = self.settings_repository.ensure_row(
                    candidate_database
                )
                server_settings = application_settings.to_server_settings(settings)
                run_startup_validations(server_settings)
                previous_database = self.runtime_database.active
                previous_configuration: LoadedDatabaseConfiguration | None = None
                previous_settings: JsonServerSettings | None = None
                if previous_database is not None:
                    previous_configuration = LoadedDatabaseConfiguration(
                        document=self.store.current().document,
                        settings=previous_database.settings,
                        sqlite_path=previous_database.db_path,
                    )
                    previous_settings = self.settings_repository.get(previous_database)

                self.runtime_database.activate(candidate_database)
                try:
                    self.activate_services(
                        LoadedDatabaseConfiguration(
                            document=None,
                            settings=settings,
                            sqlite_path=database_path,
                        ),
                        application_settings,
                    )
                    self.store.write(normalized, password=password)
                    try:
                        self.store.scrub_database_environment_keys()
                    except DatabaseConfigurationError:
                        pass
                except Exception as exc:  # noqa: BLE001
                    self.runtime_database.activate(previous_database)
                    try:
                        self.activate_services(
                            previous_configuration, previous_settings
                        )
                    except Exception:  # noqa: BLE001
                        self.application.state.lifecycle = "recovery"
                    if candidate_database is not previous_database:
                        candidate_database.dispose()
                        candidate_database = None
                    raise DatabaseSwitchError(
                        "The database could not be activated. The previous database remains active."
                    ) from exc

                self.application.state.recovery_message = None
                self.application.state.lifecycle = "ready"
                if (
                    previous_database is not None
                    and previous_database is not candidate_database
                ):
                    try:
                        previous_database.dispose()
                    except Exception:  # noqa: BLE001
                        pass
                candidate_database = None

            return self.get_status()
        except DatabaseSwitchConflict:
            raise
        except DatabaseSwitchError:
            raise
        except Exception as exc:  # noqa: BLE001
            if candidate_database is not None:
                candidate_database.dispose()
            message = (
                "The SQLite database could not be initialized. Check the path and schema."
                if normalized.backend == "sqlite"
                else "The PostgreSQL database could not be initialized. Check connectivity, permissions, and schema."
            )
            raise DatabaseSwitchError(message) from exc


__all__ = [
    "DatabaseConfigurationService",
    "DatabaseSwitchConflict",
    "DatabaseSwitchError",
]
