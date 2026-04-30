from __future__ import annotations

import os
from typing import Any

import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from FAIRS.server.common.constants import DATABASE_FILENAME, RESOURCES_PATH
from FAIRS.server.configurations import DatabaseSettings
from FAIRS.server.repositories.database.common import (
    SQLAlchemyRepositoryBase,
    normalize_table_name as normalize_table_name,
)
from FAIRS.server.repositories.schemas.models import Base

SQLITE_FOREIGN_KEYS_PRAGMA = "PRAGMA foreign_keys=ON"


# -----------------------------------------------------------------------------
def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute(SQLITE_FOREIGN_KEYS_PRAGMA)
    cursor.close()


###############################################################################
class SQLiteRepository(SQLAlchemyRepositoryBase):
    def __init__(
        self,
        settings: DatabaseSettings,
        initialize_schema: bool = False,
    ) -> None:
        self.db_path: str | None = os.path.join(RESOURCES_PATH, DATABASE_FILENAME)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.engine: Engine = sqlalchemy.create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            future=True,
        )
        event.listen(self.engine, "connect", set_sqlite_pragma)
        self.Session = sessionmaker(bind=self.engine, future=True)
        self.insert_batch_size = settings.insert_batch_size
        if initialize_schema:
            Base.metadata.create_all(self.engine)
