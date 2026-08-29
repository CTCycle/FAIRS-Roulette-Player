from __future__ import annotations

from server.common import path as shared_paths
from server.configurations import ServerSettings
from server.repositories.database.utils import is_supported_postgres_engine

###############################################################################
def run_startup_validations(settings: ServerSettings) -> None:
    for directory in (
        shared_paths.RESOURCES_PATH,
        shared_paths.LOGS_PATH,
        shared_paths.CHECKPOINT_PATH,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    if not settings.database.embedded_database:
        if not is_supported_postgres_engine(settings.database.engine):
            raise RuntimeError(
                "Unsupported database engine configured for startup: "
                f"{settings.database.engine}"
            )
