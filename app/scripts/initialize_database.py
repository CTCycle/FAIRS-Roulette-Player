from __future__ import annotations

import time


###############################################################################
if __name__ == "__main__":
    from server.bootstrap import bootstrap_runtime
    from server.common.utils.logger import logger
    from server.configurations.startup import get_server_settings
    from server.repositories.database.initializer import initialize_database

    bootstrap_runtime()
    start = time.perf_counter()
    server_settings = get_server_settings()
    logger.info("Starting database initialization")
    initialize_database(server_settings.database)
    elapsed = time.perf_counter() - start
    logger.info("Database initialization completed in %.2f seconds", elapsed)
