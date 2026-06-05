from __future__ import annotations

import os
from pathlib import Path

from server.common.path import (
    CHECKPOINT_PATH,
    CLIENT_INDEX_FILE_PATH,
    LOGS_PATH,
    RESOURCES_PATH,
)
from server.configurations import ServerSettings, get_server_settings
from server.repositories.database.utils import normalize_postgres_engine


SUPPORTED_POSTGRES_ENGINES = {
    "postgres",
    "postgresql",
    "postgresql+psycopg",
    "postgresql+psycopg2",
}


###############################################################################
def tauri_mode_enabled() -> bool:
    value = os.getenv("FAIRS_TAURI_MODE", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


###############################################################################
def run_startup_validations(settings: ServerSettings | None = None) -> None:
    resolved_settings = settings or get_server_settings()

    for directory in (RESOURCES_PATH, LOGS_PATH, CHECKPOINT_PATH):
        directory.mkdir(parents=True, exist_ok=True)

    if not resolved_settings.database.embedded_database:
        engine_name = normalize_postgres_engine(resolved_settings.database.engine).lower()
        if engine_name not in SUPPORTED_POSTGRES_ENGINES:
            raise RuntimeError(
                "Unsupported database engine configured for startup: "
                f"{resolved_settings.database.engine}"
            )

    if tauri_mode_enabled() and not CLIENT_INDEX_FILE_PATH.is_file():
        raise RuntimeError(
            "Tauri mode requires a built frontend at "
            f"{CLIENT_INDEX_FILE_PATH}."
        )
