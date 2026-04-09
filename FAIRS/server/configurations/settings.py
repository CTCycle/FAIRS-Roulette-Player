from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from FAIRS.server.common.constants import CONFIGURATIONS_FILE
from FAIRS.server.configurations.base import ensure_mapping
from FAIRS.server.configurations.bootstrap import ensure_environment_loaded
from FAIRS.server.domain.configuration import (
    DatabaseSettings,
    DeviceSettings,
    JobsSettings,
    ServerSettings,
)


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
            raise ValueError(f"External database mode requires configuration keys: {joined}")

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
class JsonConfigurationSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        raw_path = getattr(settings_cls, "_configuration_file", CONFIGURATIONS_FILE)
        self.configuration_file = Path(raw_path)

    # -------------------------------------------------------------------------
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    # -------------------------------------------------------------------------
    def __call__(self) -> dict[str, Any]:
        if not self.configuration_file.exists():
            raise RuntimeError(f"Configuration file not found: {self.configuration_file}")

        try:
            payload = json.loads(self.configuration_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unable to load configuration from {self.configuration_file}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("Configuration must be a JSON object.")

        return {
            "database": ensure_mapping(payload.get("database")),
            "jobs": ensure_mapping(payload.get("jobs")),
            "device": ensure_mapping(payload.get("device")),
        }


###############################################################################
class TechnicalEnvSettingsSource(PydanticBaseSettingsSource):
    DATABASE_ENV_MAP: ClassVar[dict[str, str]] = {
        "DATABASE_EMBEDDED_DATABASE": "embedded_database",
        "DATABASE_ENGINE": "engine",
        "DATABASE_HOST": "host",
        "DATABASE_PORT": "port",
        "DATABASE_DATABASE_NAME": "database_name",
        "DATABASE_USERNAME": "username",
        "DATABASE_PASSWORD": "password",
        "DATABASE_SSL": "ssl",
        "DATABASE_SSL_CA": "ssl_ca",
        "DATABASE_CONNECT_TIMEOUT": "connect_timeout",
        "DATABASE_INSERT_BATCH_SIZE": "insert_batch_size",
    }
    JOBS_ENV_MAP: ClassVar[dict[str, str]] = {
        "JOBS_POLLING_INTERVAL": "polling_interval",
    }
    DEVICE_ENV_MAP: ClassVar[dict[str, str]] = {
        "DEVICE_JIT_COMPILE": "jit_compile",
        "DEVICE_JIT_BACKEND": "jit_backend",
        "DEVICE_USE_MIXED_PRECISION": "use_mixed_precision",
    }

    # -------------------------------------------------------------------------
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    # -------------------------------------------------------------------------
    def __call__(self) -> dict[str, Any]:
        out: dict[str, Any] = {}

        database_env: dict[str, Any] = {}
        for env_key, target_key in self.DATABASE_ENV_MAP.items():
            raw = os.getenv(env_key)
            if raw is not None:
                database_env[target_key] = raw
        if database_env:
            out["database"] = database_env

        jobs_env: dict[str, Any] = {}
        for env_key, target_key in self.JOBS_ENV_MAP.items():
            raw = os.getenv(env_key)
            if raw is not None:
                jobs_env[target_key] = raw
        if jobs_env:
            out["jobs"] = jobs_env

        device_env: dict[str, Any] = {}
        for env_key, target_key in self.DEVICE_ENV_MAP.items():
            raw = os.getenv(env_key)
            if raw is not None:
                device_env[target_key] = raw
        if device_env:
            out["device"] = device_env

        return out


###############################################################################
class UnifiedEnvironmentSettingsSource(PydanticBaseSettingsSource):
    def __init__(
        self,
        settings_cls: type[BaseSettings],
        env_settings_source: PydanticBaseSettingsSource,
    ) -> None:
        super().__init__(settings_cls)
        self._env_settings_source = env_settings_source
        self._technical_env_source = TechnicalEnvSettingsSource(settings_cls)

    # -------------------------------------------------------------------------
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    # -------------------------------------------------------------------------
    def __call__(self) -> dict[str, Any]:
        merged = ensure_mapping(self._env_settings_source())
        technical_overrides = ensure_mapping(self._technical_env_source())

        for section in ("database", "jobs", "device"):
            technical_payload = technical_overrides.get(section)
            if not isinstance(technical_payload, dict):
                continue

            current = merged.get(section)
            if not isinstance(current, dict):
                current = {}
            current.update(technical_payload)
            merged[section] = current

        return merged


###############################################################################
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    _configuration_file: ClassVar[str] = CONFIGURATIONS_FILE

    database: JsonDatabaseSettings = Field(default_factory=JsonDatabaseSettings)
    jobs: JsonJobsSettings = Field(default_factory=JsonJobsSettings)
    device: JsonDeviceSettings = Field(default_factory=JsonDeviceSettings)

    fastapi_host: str = "127.0.0.1"
    fastapi_port: int = Field(default=8000, ge=1, le=65535)
    ui_host: str = "127.0.0.1"
    ui_port: int = Field(default=8001, ge=1, le=65535)
    enable_api_docs: bool = True
    fairs_allow_direct_api_routes: bool = True
    fairs_tauri_mode: bool = False
    reload: bool = False
    optional_dependencies: bool = False
    mplbackend: str | None = None
    keras_backend: str | None = None

    @field_validator("fastapi_host", "ui_host", "mplbackend", "keras_backend", mode="before")
    @classmethod
    def normalize_runtime_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        _ = dotenv_settings
        return (
            init_settings,
            UnifiedEnvironmentSettingsSource(settings_cls, env_settings),
            JsonConfigurationSettingsSource(settings_cls),
            file_secret_settings,
        )

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


# -----------------------------------------------------------------------------
def _build_path_scoped_settings_class(config_path: str) -> type[AppSettings]:
    class PathScopedAppSettings(AppSettings):
        _configuration_file: ClassVar[str] = config_path

    return PathScopedAppSettings


# -----------------------------------------------------------------------------
def _load_app_settings(settings_cls: type[AppSettings]) -> AppSettings:
    ensure_environment_loaded()
    try:
        return settings_cls()
    except ValidationError as exc:
        raise RuntimeError(f"Invalid application settings: {exc}") from exc


###############################################################################
@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return _load_app_settings(AppSettings)


# -----------------------------------------------------------------------------
def get_server_settings(config_path: str | None = None) -> ServerSettings:
    if config_path:
        scoped_class = _build_path_scoped_settings_class(config_path=config_path)
        return _load_app_settings(scoped_class).to_server_settings()
    return get_app_settings().to_server_settings()


# -----------------------------------------------------------------------------
def reload_settings_for_tests() -> AppSettings:
    get_app_settings.cache_clear()
    return get_app_settings()
