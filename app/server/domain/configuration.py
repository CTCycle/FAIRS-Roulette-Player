from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

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
    use_mixed_precision: bool


###############################################################################
@dataclass(frozen=True)
class ServerSettings:
    database: DatabaseSettings
    jobs: JobsSettings
    device: DeviceSettings


###############################################################################
class JsonDatabaseSettings(BaseModel):
    embedded_database: bool = True
    engine: str = "postgres"
    host: str | None = None
    port: int = Field(default=5432, ge=1, le=65535)
    database_name: str | None = None
    username: str | None = None
    password: str | None = None
    ssl: bool = False
    ssl_ca: str | None = None
    connect_timeout: int = Field(default=10, ge=1)
    insert_batch_size: int = Field(default=1000, ge=1)

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

    @field_validator("engine", mode="before")
    @classmethod
    def normalize_engine(cls, value: Any) -> str:
        text = str(value).strip() if value is not None else ""
        return text or "postgres"

    @model_validator(mode="after")
    def validate_external_database_requirements(self) -> "JsonDatabaseSettings":
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
    polling_interval: float = Field(default=1.0, ge=0.1, le=10.0)


###############################################################################
class JsonDeviceSettings(BaseModel):
    jit_compile: bool = False
    jit_backend: str = "inductor"
    use_mixed_precision: bool = False

    @field_validator("jit_backend", mode="before")
    @classmethod
    def normalize_backend(cls, value: Any) -> str:
        text = str(value).strip() if value is not None else ""
        return text or "inductor"


###############################################################################
class JsonServerSettings(BaseModel):
    database: JsonDatabaseSettings = Field(default_factory=JsonDatabaseSettings)
    jobs: JsonJobsSettings = Field(default_factory=JsonJobsSettings)
    device: JsonDeviceSettings = Field(default_factory=JsonDeviceSettings)

    # -------------------------------------------------------------------------
    def to_server_settings(self) -> ServerSettings:
        db = self.database
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
                use_mixed_precision=self.device.use_mixed_precision,
            ),
        )

    # -------------------------------------------------------------------------
    def to_blocks(self) -> dict[str, dict[str, Any]]:
        return {
            "database": self.database.model_dump(),
            "jobs": self.jobs.model_dump(),
            "device": self.device.model_dump(),
        }
