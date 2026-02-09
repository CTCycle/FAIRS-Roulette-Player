from __future__ import annotations

from FAIRS.server.repositories.database.backend import (
    BACKEND_FACTORIES,
    DatabaseBackend,
    FAIRSDatabase,
    database,
)
from FAIRS.server.repositories.database.initializer import initialize_database
from FAIRS.server.repositories.database.postgres import PostgresRepository
from FAIRS.server.repositories.database.sqlite import SQLiteRepository
