from __future__ import annotations

import time


def main() -> int:
    from server.bootstrap import bootstrap_runtime
    from server.common.utils.logger import logger
    from server.configurations.startup import get_server_settings
    from server.repositories.database.initializer import (
        DatabaseInitializationError,
        initialize_database,
    )

    bootstrap_runtime()
    start = time.perf_counter()
    server_settings = get_server_settings()
    logger.info("Starting database create/upgrade")
    try:
        initialize_database(server_settings.database)
    except DatabaseInitializationError as exc:
        logger.error("Database create/upgrade failed: %s", exc)
        return 1
    elapsed = time.perf_counter() - start
    logger.info("Database create/upgrade completed in %.2f seconds", elapsed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
