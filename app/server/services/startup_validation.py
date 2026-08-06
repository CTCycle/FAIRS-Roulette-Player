from __future__ import annotations

import os

from server.common import path as shared_paths
from server.configurations import ServerSettings, get_server_settings
from server.repositories.database.utils import is_supported_postgres_engine

###############################################################################
def tauri_mode_enabled() -> bool:
    value = os.getenv("FAIRS_TAURI_MODE", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}

###############################################################################
def run_startup_validations(settings: ServerSettings | None = None) -> None:
    resolved_settings = settings or get_server_settings()

    for directory in (
        shared_paths.RESOURCES_PATH,
        shared_paths.LOGS_PATH,
        shared_paths.CHECKPOINT_PATH,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    if not resolved_settings.database.embedded_database:
        if not is_supported_postgres_engine(resolved_settings.database.engine):
            raise RuntimeError(
                "Unsupported database engine configured for startup: "
                f"{resolved_settings.database.engine}"
            )

    if tauri_mode_enabled() and not shared_paths.CLIENT_INDEX_FILE_PATH.is_file():
        raise RuntimeError(
            "Tauri mode requires a built frontend at "
            f"{shared_paths.CLIENT_INDEX_FILE_PATH}."
        )
