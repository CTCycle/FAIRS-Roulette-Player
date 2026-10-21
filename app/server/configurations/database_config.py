# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Literal

from dotenv import dotenv_values
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from server.common import path as shared_paths
from server.contracts.configuration import DatabaseSettings
from server.contracts.database_configuration import (
    DatabaseConfigurationInput,
    DatabaseConfigurationResponse,
    database_settings_from_input,
    public_configuration,
)

DATABASE_ENV_KEYS = frozenset({
    "DATABASE_URL",
    "EMBEDDED_DATABASE",
    "DATABASE_ENGINE",
    "DATABASE_HOST",
    "DATABASE_PORT",
    "DATABASE_NAME",
    "DATABASE_USERNAME",
    "DATABASE_PASSWORD",
    "DATABASE_SSL",
    "DATABASE_SSL_CA",
    "DATABASE_CONNECT_TIMEOUT",
    "DATABASE_INSERT_BATCH_SIZE",
})


class DatabaseConfigurationError(RuntimeError):
    """Raised when the standalone connection configuration is unusable."""


class SQLiteFileConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    path: str
    insert_batch_size: int = Field(ge=1, le=100000)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("SQLite database path must not be blank.")
        return normalized


class PostgreSQLFileConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    engine: Literal["postgresql+psycopg"] = "postgresql+psycopg"
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    database_name: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password_protected: str | None = None
    ssl: bool = False
    ssl_ca: str | None = None
    connect_timeout: int = Field(ge=1, le=300)
    insert_batch_size: int = Field(ge=1, le=100000)

    @field_validator("host", "database_name", "username")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("PostgreSQL connection values must not be blank.")
        return normalized


class DatabaseConfigurationFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    backend: Literal["sqlite", "postgresql"]
    sqlite: SQLiteFileConfiguration | None = None
    postgresql: PostgreSQLFileConfiguration | None = None

    @model_validator(mode="after")
    def validate_backend_shape(self) -> "DatabaseConfigurationFile":
        if self.backend == "sqlite" and (self.sqlite is None or self.postgresql is not None):
            raise ValueError("SQLite configuration must contain only the sqlite block.")
        if self.backend == "postgresql" and (
            self.postgresql is None or self.sqlite is not None
        ):
            raise ValueError("PostgreSQL configuration must contain only the postgresql block.")
        return self


@dataclass(frozen=True)
class LoadedDatabaseConfiguration:
    document: DatabaseConfigurationFile | None
    settings: DatabaseSettings
    sqlite_path: Path | None


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _dpapi_transform(value: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise DatabaseConfigurationError(
            "PostgreSQL passwords can only be protected on Windows with DPAPI."
        )
    source_buffer = ctypes.create_string_buffer(value)
    source = _DataBlob(
        len(value), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte))
    )
    result = _DataBlob()
    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    if protect:
        ok = crypt32.CryptProtectData(
            ctypes.byref(source),
            "FAIRS database password",
            None,
            None,
            None,
            0x1,
            ctypes.byref(result),
        )
    else:
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            0x1,
            ctypes.byref(result),
        )
    if not ok:
        raise DatabaseConfigurationError("Unable to protect or decrypt the saved password.")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)


def protect_password(password: str) -> str:
    encrypted = _dpapi_transform(password.encode("utf-8"), protect=True)
    return base64.b64encode(encrypted).decode("ascii")


def unprotect_password(encrypted: str) -> str:
    try:
        raw = base64.b64decode(encrypted, validate=True)
        return _dpapi_transform(raw, protect=False).decode("utf-8")
    except DatabaseConfigurationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DatabaseConfigurationError("Unable to decrypt the saved password.") from exc


class DatabaseConfigurationStore:
    """Owns atomic, DB-independent database configuration and legacy migration."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        environment_file: str | Path | None = None,
        password_protector=protect_password,
        password_unprotector=unprotect_password,
    ) -> None:
        self.path = Path(path) if path is not None else shared_paths.DATABASE_CONFIG_FILE
        self.environment_file = (
            Path(environment_file)
            if environment_file is not None
            else shared_paths.ENV_FILE_PATH
        )
        self._protect = password_protector
        self._unprotect = password_unprotector

    @staticmethod
    def _default_input() -> DatabaseConfigurationInput:
        return DatabaseConfigurationInput(
            backend="sqlite",
            sqlite_path=str(shared_paths.DATABASE_PATH.resolve()),
        )

    def _read_document(self) -> DatabaseConfigurationFile:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return DatabaseConfigurationFile.model_validate(payload)
        except FileNotFoundError:
            raise
        except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise DatabaseConfigurationError(
                "The database configuration file is invalid. Review it or save a valid configuration in Settings."
            ) from exc

    def _settings_from_document(
        self, document: DatabaseConfigurationFile
    ) -> LoadedDatabaseConfiguration:
        if document.backend == "sqlite":
            assert document.sqlite is not None
            path = Path(document.sqlite.path).expanduser().resolve()
            settings = DatabaseSettings(
                embedded_database=True,
                engine=None,
                host=None,
                port=None,
                database_name=None,
                username=None,
                password=None,
                ssl=False,
                ssl_ca=None,
                connect_timeout=10,
                insert_batch_size=document.sqlite.insert_batch_size,
            )
            return LoadedDatabaseConfiguration(document, settings, path)

        assert document.postgresql is not None
        block = document.postgresql
        password = (
            self._unprotect(block.password_protected)
            if block.password_protected
            else None
        )
        settings = DatabaseSettings(
            embedded_database=False,
            engine=block.engine,
            host=block.host,
            port=block.port,
            database_name=block.database_name,
            username=block.username,
            password=password,
            ssl=block.ssl,
            ssl_ca=block.ssl_ca,
            connect_timeout=block.connect_timeout,
            insert_batch_size=block.insert_batch_size,
        )
        return LoadedDatabaseConfiguration(document, settings, None)

    def current(self) -> LoadedDatabaseConfiguration:
        return self._settings_from_document(self._read_document())

    def load_or_migrate(self) -> LoadedDatabaseConfiguration:
        if self.path.exists():
            loaded = self.current()
            self.remove_legacy_environment_keys()
            return loaded

        candidate = self._legacy_environment_input()
        self.write(candidate, password=candidate.password)
        self.remove_legacy_environment_keys()
        return self.current()

    def _legacy_environment_input(self) -> DatabaseConfigurationInput:
        raw = dotenv_values(self.environment_file) if self.environment_file.exists() else {}
        if raw.get("DATABASE_URL"):
            raise DatabaseConfigurationError(
                "Legacy DATABASE_URL cannot be migrated. Configure SQLite or postgresql+psycopg in Settings."
            )
        embedded = str(raw.get("EMBEDDED_DATABASE", "true")).strip().lower()
        if embedded not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
            raise DatabaseConfigurationError("Legacy EMBEDDED_DATABASE must be a boolean.")
        if embedded in {"true", "1", "yes", "on"}:
            return self._default_input()
        engine = str(raw.get("DATABASE_ENGINE") or "postgresql+psycopg").strip().lower()
        if engine != "postgresql+psycopg":
            raise DatabaseConfigurationError("Only postgresql+psycopg can be migrated from settings/.env.")
        try:
            return DatabaseConfigurationInput(
                backend="postgresql",
                host=raw.get("DATABASE_HOST"),
                port=raw.get("DATABASE_PORT") or 5432,
                database_name=raw.get("DATABASE_NAME"),
                username=raw.get("DATABASE_USERNAME"),
                password=raw.get("DATABASE_PASSWORD"),
                ssl=str(raw.get("DATABASE_SSL", "false")).strip().lower()
                in {"true", "1", "yes", "on"},
                ssl_ca=raw.get("DATABASE_SSL_CA"),
                connect_timeout=raw.get("DATABASE_CONNECT_TIMEOUT") or 10,
                insert_batch_size=raw.get("DATABASE_INSERT_BATCH_SIZE") or 1000,
            )
        except ValidationError as exc:
            raise DatabaseConfigurationError(
                "Legacy database values in settings/.env are incomplete or invalid."
            ) from exc

    def resolve_input(
        self, candidate: DatabaseConfigurationInput
    ) -> tuple[DatabaseConfigurationInput, str | None]:
        password = candidate.password or None
        if candidate.backend == "postgresql" and not password and not candidate.clear_password:
            try:
                current = self.current()
            except DatabaseConfigurationError:
                current = None
            if current is not None and current.document.backend == "postgresql":
                password = current.settings.password
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
        return normalized, None if candidate.clear_password else password

    def write(
        self,
        candidate: DatabaseConfigurationInput,
        *,
        password: str | None = None,
    ) -> LoadedDatabaseConfiguration:
        if candidate.backend == "sqlite":
            assert candidate.sqlite_path is not None
            document = DatabaseConfigurationFile(
                schema_version=1,
                backend="sqlite",
                sqlite=SQLiteFileConfiguration(
                    path=str(Path(candidate.sqlite_path).expanduser().resolve()),
                    insert_batch_size=candidate.insert_batch_size,
                ),
            )
        else:
            protected = self._protect(password) if password else None
            document = DatabaseConfigurationFile(
                schema_version=1,
                backend="postgresql",
                postgresql=PostgreSQLFileConfiguration(
                    host=candidate.host.strip(),  # type: ignore[union-attr]
                    port=candidate.port,
                    database_name=candidate.database_name.strip(),  # type: ignore[union-attr]
                    username=candidate.username.strip(),  # type: ignore[union-attr]
                    password_protected=protected,
                    ssl=candidate.ssl,
                    ssl_ca=candidate.ssl_ca.strip() if candidate.ssl_ca else None,
                    connect_timeout=candidate.connect_timeout,
                    insert_batch_size=candidate.insert_batch_size,
                ),
            )
        self._atomic_write(document)
        return self._settings_from_document(document)

    def _atomic_write(self, document: DatabaseConfigurationFile) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(
                    json.dumps(
                        document.model_dump(mode="json", exclude_none=True),
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n"
                )
                temporary.flush()
                os.fsync(temporary.fileno())
            try:
                os.chmod(temporary_path, 0o600)
            except OSError:
                pass
            os.replace(temporary_path, self.path)
            temporary_path = None
        except OSError as exc:
            raise DatabaseConfigurationError(
                "Unable to write the database configuration file."
            ) from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def remove_legacy_environment_keys(self) -> None:
        if not self.environment_file.is_file():
            return
        original = self.environment_file.read_text(encoding="utf-8").splitlines(keepends=True)
        preserved = []
        for line in original:
            stripped = line.lstrip()
            if not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
                preserved.append(line)
                continue
            key = stripped.split("=", 1)[0].strip()
            if key not in DATABASE_ENV_KEYS:
                preserved.append(line)
        if len(preserved) == len(original):
            return
        self._atomic_text_write(self.environment_file, "".join(preserved))

    @staticmethod
    def _atomic_text_write(path: Path, content: str) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        except OSError as exc:
            raise DatabaseConfigurationError(
                "Unable to remove legacy database values from settings/.env."
            ) from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @staticmethod
    def to_public(
        loaded: LoadedDatabaseConfiguration | None,
    ) -> DatabaseConfigurationResponse | None:
        if loaded is None:
            return None
        document = loaded.document
        if document is None:
            return None
        if document.backend == "sqlite":
            assert document.sqlite is not None
            return public_configuration(
                backend="sqlite",
                sqlite_path=document.sqlite.path,
                insert_batch_size=document.sqlite.insert_batch_size,
            )
        assert document.postgresql is not None
        block = document.postgresql
        return public_configuration(
            backend="postgresql",
            host=block.host,
            port=block.port,
            database_name=block.database_name,
            username=block.username,
            password_configured=bool(block.password_protected),
            ssl=block.ssl,
            ssl_ca=block.ssl_ca,
            connect_timeout=block.connect_timeout,
            insert_batch_size=block.insert_batch_size,
        )


__all__ = [
    "DATABASE_ENV_KEYS",
    "DatabaseConfigurationError",
    "DatabaseConfigurationFile",
    "DatabaseConfigurationStore",
    "LoadedDatabaseConfiguration",
]
