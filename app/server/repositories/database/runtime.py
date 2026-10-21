# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from threading import Condition
import time


from server.repositories.database.backend import FAIRSDatabase


###############################################################################
class DatabaseUnavailableError(RuntimeError):
    """Raised when database-backed routes are unavailable during recovery."""


###############################################################################
class DatabaseSwitchConflict(RuntimeError):
    """Raised when a switch conflicts with active work or database operations."""


###############################################################################
class _ManagedSessionFactory:

    # -------------------------------------------------------------------------
    def __init__(self, owner: "RuntimeDatabaseManager") -> None:
        self.owner = owner

    # -------------------------------------------------------------------------
    def __call__(self):
        return self.owner.session()

    # -------------------------------------------------------------------------
    def begin(self):
        return self.owner.session_transaction()


###############################################################################
class RuntimeDatabaseManager:
    """Stable repository target that can atomically replace its SQLAlchemy owner."""

    # -------------------------------------------------------------------------
    def __init__(self, database: FAIRSDatabase | None = None) -> None:
        self._condition = Condition()
        self._database = database
        self._in_flight = 0
        self._switching = False
        self.Session = _ManagedSessionFactory(self)

    # -------------------------------------------------------------------------
    @property
    def active(self) -> FAIRSDatabase | None:
        with self._condition:
            return self._database

    # -------------------------------------------------------------------------
    @property
    def is_switching(self) -> bool:
        with self._condition:
            return self._switching

    # -------------------------------------------------------------------------
    @property
    def settings(self):
        return self._required_database().settings

    # -------------------------------------------------------------------------
    @property
    def db_path(self):
        return self._required_database().db_path

    # -------------------------------------------------------------------------
    @property
    def insert_batch_size(self) -> int:
        return self._required_database().insert_batch_size

    # -------------------------------------------------------------------------
    def _required_database(self) -> FAIRSDatabase:
        database = self.active
        if database is None:
            raise DatabaseUnavailableError("Database services are in recovery mode.")
        return database

    # -------------------------------------------------------------------------
    @contextmanager
    def operation(self) -> Iterator[None]:
        with self._condition:
            if self._switching:
                raise DatabaseSwitchConflict(
                    "Database switching is in progress. Retry the request shortly."
                )
            if self._database is None:
                raise DatabaseUnavailableError("Database services are in recovery mode.")
            self._in_flight += 1
        try:
            yield
        finally:
            with self._condition:
                self._in_flight -= 1
                self._condition.notify_all()

    # -------------------------------------------------------------------------
    @contextmanager
    def session(self):
        with self.operation():
            database = self._required_database()
            with database.Session() as session:
                yield session

    # -------------------------------------------------------------------------
    @contextmanager
    def session_transaction(self):
        with self.operation():
            database = self._required_database()
            with database.Session.begin() as session:
                yield session

    # -------------------------------------------------------------------------
    @contextmanager
    def transaction(self):
        with self.operation():
            database = self._required_database()
            with database.transaction() as session:
                yield session

    # -------------------------------------------------------------------------
    @contextmanager
    def switching(self, timeout_seconds: float = 10.0):
        deadline = time.monotonic() + timeout_seconds
        with self._condition:
            if self._switching:
                raise DatabaseSwitchConflict("Another database switch is already in progress.")
            self._switching = True
            while self._in_flight:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._switching = False
                    self._condition.notify_all()
                    raise DatabaseSwitchConflict(
                        "Database operations are still active. Retry the switch when they finish."
                    )
                self._condition.wait(timeout=remaining)
        try:
            yield
        finally:
            with self._condition:
                self._switching = False
                self._condition.notify_all()

    # -------------------------------------------------------------------------
    def activate(self, database: FAIRSDatabase | None) -> FAIRSDatabase | None:
        with self._condition:
            if not self._switching:
                raise RuntimeError("Database activation requires the switch lock.")
            previous = self._database
            self._database = database
            return previous

    # -------------------------------------------------------------------------
    def dispose(self) -> None:
        database = self.active
        if database is not None:
            database.dispose()


__all__ = [
    "DatabaseSwitchConflict",
    "DatabaseUnavailableError",
    "RuntimeDatabaseManager",
]
