# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

from dataclasses import dataclass
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

    def to_server_settings(self, database: DatabaseSettings) -> ServerSettings:
        return ServerSettings(
            database=database,
            jobs=JobsSettings(polling_interval=self.jobs.polling_interval),
            device=DeviceSettings(
                jit_compile=self.device.jit_compile,
                jit_backend=self.device.jit_backend,
            ),
            roulette=self.roulette.to_runtime_settings(),
        )
