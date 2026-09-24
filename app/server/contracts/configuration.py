from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

JIT_BACKEND_MAX_LENGTH = 64
JIT_BACKEND_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
_JIT_BACKEND_PATTERN = re.compile(JIT_BACKEND_PATTERN)

###############################################################################
def normalize_jit_backend(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("jit_backend must be a string.")
    text = value.strip()
    if not text:
        raise ValueError("jit_backend must not be blank.")
    if len(text) > JIT_BACKEND_MAX_LENGTH:
        raise ValueError(
            f"jit_backend must be {JIT_BACKEND_MAX_LENGTH} characters or fewer."
        )
    if _JIT_BACKEND_PATTERN.fullmatch(text) is None:
        raise ValueError(
            "jit_backend may contain only letters, numbers, '.', '_', ':', and '-'."
        )
    if text not in {"eager", "inductor"}:
        raise ValueError("jit_backend must be either 'eager' or 'inductor'.")
    return text

###############################################################################
@dataclass(frozen=True)
class DatabaseSettings:
    embedded_database: bool
    engine: str | None
    host: str | None
    port: int | None
    database_name: str | None
    username: str | None
    password: str | None
    ssl: bool
    ssl_ca: str | None
    connect_timeout: int
    insert_batch_size: int

###############################################################################
@dataclass(frozen=True)
class JobsSettings:
    polling_interval: float

###############################################################################
@dataclass(frozen=True)
class DeviceSettings:
    jit_compile: bool
    jit_backend: str

###############################################################################
@dataclass(frozen=True)
class RouletteSettings:
    minimum_number: int = 0
    maximum_number: int = 36
    exclude_zero: bool = False
    invert_colors: bool = False
    show_number_labels: bool = True

###############################################################################
@dataclass(frozen=True)
class ServerSettings:
    database: DatabaseSettings
    jobs: JobsSettings
    device: DeviceSettings
    roulette: RouletteSettings = RouletteSettings()

###############################################################################
class EnvDatabaseSettings(BaseModel):
    embedded_database: bool = True
    engine: str = "postgresql+psycopg"
    host: str | None = None
    port: int = Field(default=5432, ge=1, le=65535)
    database_name: str | None = None
    username: str | None = None
    password: str | None = None
    ssl: bool = False
    ssl_ca: str | None = None
    connect_timeout: int = Field(default=10, ge=1)
    insert_batch_size: int = Field(default=1000, ge=1)

    # -------------------------------------------------------------------------
    @field_validator(
        "host",
        "database_name",
        "username",
        "password",
        "ssl_ca",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    # -------------------------------------------------------------------------
    @field_validator("engine", mode="before")
    @classmethod
    def normalize_engine(cls, value: Any) -> str:
        text = str(value).strip() if value is not None else ""
        return text or "postgresql+psycopg"

    # -------------------------------------------------------------------------
    @classmethod
    def from_environment(cls) -> "EnvDatabaseSettings":
        raw: dict[str, Any] = {}
        database_url = os.getenv("DATABASE_URL")
        if database_url is not None and database_url.strip():
            raise ValueError(
                "DATABASE_URL is unsupported. Configure the individual DATABASE_* values."
            )

        env_to_field = {
            "EMBEDDED_DATABASE": "embedded_database",
            "DATABASE_ENGINE": "engine",
            "DATABASE_HOST": "host",
            "DATABASE_PORT": "port",
            "DATABASE_NAME": "database_name",
            "DATABASE_USERNAME": "username",
            "DATABASE_PASSWORD": "password",
            "DATABASE_SSL": "ssl",
            "DATABASE_SSL_CA": "ssl_ca",
            "DATABASE_CONNECT_TIMEOUT": "connect_timeout",
            "DATABASE_INSERT_BATCH_SIZE": "insert_batch_size",
        }
        for env_name, field_name in env_to_field.items():
            value = os.getenv(env_name)
            if value is not None:
                raw[field_name] = value

        return cls.model_validate(raw)

    # -------------------------------------------------------------------------
    @model_validator(mode="after")
    def validate_external_database_requirements(self) -> "EnvDatabaseSettings":
        if self.embedded_database:
            return self

        missing: list[str] = []
        if not self.host:
            missing.append("database.host")
        if not self.database_name:
            missing.append("database.database_name")
        if not self.username:
            missing.append("database.username")

        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                f"External database mode requires configuration keys: {joined}"
            )
        return self

###############################################################################
class JsonJobsSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    polling_interval: float = Field(default=1.0, ge=0.1, le=10.0)

###############################################################################
class JsonDeviceSettings(BaseModel):
    """Process-wide compiler settings, not per-training device preferences."""

    model_config = ConfigDict(extra="forbid")

    jit_compile: bool = False
    jit_backend: str = Field(
        default="eager",
        max_length=JIT_BACKEND_MAX_LENGTH,
        pattern=JIT_BACKEND_PATTERN,
    )

    # -------------------------------------------------------------------------
    @field_validator("jit_backend", mode="before")
    @classmethod
    def normalize_backend(cls, value: Any) -> str:
        return normalize_jit_backend(value)

###############################################################################
class JsonRouletteSettings(BaseModel):
    """Application-wide roulette outcome and visualization settings."""

    model_config = ConfigDict(extra="forbid")

    minimum_number: int = Field(default=0, ge=0, le=36)
    maximum_number: int = Field(default=36, ge=0, le=36)
    exclude_zero: bool = False
    invert_colors: bool = False
    show_number_labels: bool = True

    # -------------------------------------------------------------------------
    @model_validator(mode="after")
    def validate_number_pool(self) -> "JsonRouletteSettings":
        if self.minimum_number > self.maximum_number:
            raise ValueError("minimum_number must be less than or equal to maximum_number.")
        if self.exclude_zero and self.minimum_number == 0 and self.maximum_number == 0:
            raise ValueError("Roulette number pool must contain at least one number.")
        return self

    # -------------------------------------------------------------------------
    def to_runtime_settings(self) -> RouletteSettings:
        return RouletteSettings(
            minimum_number=self.minimum_number,
            maximum_number=self.maximum_number,
            exclude_zero=self.exclude_zero,
            invert_colors=self.invert_colors,
            show_number_labels=self.show_number_labels,
        )

###############################################################################
class JsonServerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: JsonJobsSettings = Field(default_factory=JsonJobsSettings)
    device: JsonDeviceSettings = Field(default_factory=JsonDeviceSettings)
    roulette: JsonRouletteSettings = Field(default_factory=JsonRouletteSettings)

    # -------------------------------------------------------------------------
    @model_validator(mode="before")
    @classmethod
    def reject_database_block(cls, value: Any) -> Any:
        if isinstance(value, dict) and "database" in value:
            raise ValueError(
                "Database configuration must be provided via settings/.env."
            )
        return value

    # -------------------------------------------------------------------------
    def to_server_settings(self) -> ServerSettings:
        db = EnvDatabaseSettings.from_environment()
        if db.embedded_database:
            database_settings = DatabaseSettings(
                embedded_database=True,
                engine=None,
                host=None,
                port=None,
                database_name=None,
                username=None,
                password=None,
                ssl=False,
                ssl_ca=None,
                connect_timeout=db.connect_timeout,
                insert_batch_size=db.insert_batch_size,
            )
        else:
            database_settings = DatabaseSettings(
                embedded_database=False,
                engine=db.engine.strip().lower(),
                host=db.host,
                port=db.port,
                database_name=db.database_name,
                username=db.username,
                password=db.password,
                ssl=db.ssl,
                ssl_ca=db.ssl_ca,
                connect_timeout=db.connect_timeout,
                insert_batch_size=db.insert_batch_size,
            )

        return ServerSettings(
            database=database_settings,
            jobs=JobsSettings(polling_interval=self.jobs.polling_interval),
            device=DeviceSettings(
                jit_compile=self.device.jit_compile,
                jit_backend=self.device.jit_backend,
            ),
            roulette=self.roulette.to_runtime_settings(),
        )

    # -------------------------------------------------------------------------
    def to_blocks(self) -> dict[str, dict[str, Any]]:
        database = EnvDatabaseSettings.from_environment()
        return {
            "database": database.model_dump(),
            "jobs": self.jobs.model_dump(),
            "device": self.device.model_dump(),
            "roulette": self.roulette.model_dump(),
        }
