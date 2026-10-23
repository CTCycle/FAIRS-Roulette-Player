# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from server.contracts.configuration import DatabaseSettings

###############################################################################
class DatabaseConfigurationInput(BaseModel):
    """Editable database connection details accepted by the Settings UI."""

    model_config = ConfigDict(extra="forbid")

    backend: Literal["sqlite", "postgresql"]
    sqlite_path: str | None = None
    host: str | None = None
    port: int = Field(default=5432, ge=1, le=65535)
    database_name: str | None = None
    username: str | None = None
    password: str | None = None
    clear_password: bool = False
    ssl: bool = False
    ssl_ca: str | None = None
    connect_timeout: int = Field(default=10, ge=1, le=300)
    insert_batch_size: int = Field(default=1000, ge=1, le=100000)

    # -------------------------------------------------------------------------
    @model_validator(mode="after")
    def validate_backend_fields(self) -> "DatabaseConfigurationInput":
        if self.backend == "sqlite":
            if not self.sqlite_path or not self.sqlite_path.strip():
                raise ValueError("A SQLite database file path is required.")
        else:
            missing = [
                label
                for label, value in (
                    ("host", self.host),
                    ("database name", self.database_name),
                    ("username", self.username),
                )
                if not value or not value.strip()
            ]
            if missing:
                raise ValueError(
                    "PostgreSQL requires " + ", ".join(missing) + "."
                )
            if self.clear_password and self.password:
                raise ValueError("Provide a password or clear it, not both.")
        return self

###############################################################################
class DatabaseConfigurationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: Literal["sqlite", "postgresql"]
    sqlite_path: str | None = None
    host: str | None = None
    port: int | None = None
    database_name: str | None = None
    username: str | None = None
    password_configured: bool = False
    ssl: bool = False
    ssl_ca: str | None = None
    connect_timeout: int = 10
    insert_batch_size: int = 1000

###############################################################################
class DatabaseStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configuration: DatabaseConfigurationResponse | None
    active_backend: Literal["sqlite", "postgresql"] | None
    status: Literal["ready", "recovery", "testing"]
    message: str | None = None

###############################################################################
class DatabaseTestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    message: str

###############################################################################
def database_settings_from_input(
    candidate: DatabaseConfigurationInput,
    password: str | None,
) -> DatabaseSettings:
    if candidate.backend == "sqlite":
        return DatabaseSettings(
            embedded_database=True,
            engine=None,
            host=None,
            port=None,
            database_name=None,
            username=None,
            password=None,
            ssl=False,
            ssl_ca=None,
            connect_timeout=candidate.connect_timeout,
            insert_batch_size=candidate.insert_batch_size,
        )
    return DatabaseSettings(
        embedded_database=False,
        engine="postgresql+psycopg",
        host=candidate.host.strip() if candidate.host else None,
        port=candidate.port,
        database_name=candidate.database_name.strip() if candidate.database_name else None,
        username=candidate.username.strip() if candidate.username else None,
        password=password,
        ssl=candidate.ssl,
        ssl_ca=candidate.ssl_ca.strip() if candidate.ssl_ca else None,
        connect_timeout=candidate.connect_timeout,
        insert_batch_size=candidate.insert_batch_size,
    )

###############################################################################
def public_configuration(
    *,
    backend: str,
    sqlite_path: str | None = None,
    host: str | None = None,
    port: int | None = None,
    database_name: str | None = None,
    username: str | None = None,
    password_configured: bool = False,
    ssl: bool = False,
    ssl_ca: str | None = None,
    connect_timeout: int = 10,
    insert_batch_size: int = 1000,
) -> DatabaseConfigurationResponse:
    return DatabaseConfigurationResponse(
        backend=backend,
        sqlite_path=sqlite_path,
        host=host,
        port=port,
        database_name=database_name,
        username=username,
        password_configured=password_configured,
        ssl=ssl,
        ssl_ca=ssl_ca,
        connect_timeout=connect_timeout,
        insert_batch_size=insert_batch_size,
    )
