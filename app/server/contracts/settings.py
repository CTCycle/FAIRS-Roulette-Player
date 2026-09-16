from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from server.contracts.configuration import (
    JIT_BACKEND_MAX_LENGTH,
    JIT_BACKEND_PATTERN,
    JsonServerSettings,
    normalize_jit_backend,
)

###############################################################################
class SettingsJobsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    polling_interval: float | None = Field(
        default=None,
        ge=0.1,
        le=10.0,
        description="Training and status polling cadence in seconds.",
    )

    # -------------------------------------------------------------------------
    @model_validator(mode="after")
    def reject_explicit_null(self) -> "SettingsJobsPatch":
        if "polling_interval" in self.model_fields_set and self.polling_interval is None:
            raise ValueError("polling_interval must be a number.")
        return self


###############################################################################
class SettingsDevicePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jit_compile: bool | None = Field(
        default=None,
        description="Whether newly constructed training models use JIT compilation.",
    )
    jit_backend: str | None = Field(
        default=None,
        max_length=JIT_BACKEND_MAX_LENGTH,
        pattern=JIT_BACKEND_PATTERN,
        description="Backend name used for newly constructed JIT-enabled models.",
    )

    # -------------------------------------------------------------------------
    @field_validator("jit_backend", mode="before")
    @classmethod
    def normalize_backend(cls, value: Any) -> str | None:
        if value is None:
            return None
        return normalize_jit_backend(value)

    # -------------------------------------------------------------------------
    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "SettingsDevicePatch":
        if "jit_compile" in self.model_fields_set and self.jit_compile is None:
            raise ValueError("jit_compile must be a boolean.")
        if "jit_backend" in self.model_fields_set and self.jit_backend is None:
            raise ValueError("jit_backend must be a string.")
        return self


###############################################################################
class SettingsPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: SettingsJobsPatch | None = None
    device: SettingsDevicePatch | None = None

    # -------------------------------------------------------------------------
    @model_validator(mode="after")
    def reject_explicit_null_blocks(self) -> "SettingsPatchRequest":
        if "jobs" in self.model_fields_set and self.jobs is None:
            raise ValueError("jobs must be an object.")
        if "device" in self.model_fields_set and self.device is None:
            raise ValueError("device must be an object.")
        return self


###############################################################################
class SettingsJobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    polling_interval: float = Field(
        ge=0.1,
        le=10.0,
        description="Training and status polling cadence in seconds.",
    )


###############################################################################
class SettingsDeviceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jit_compile: bool
    jit_backend: str = Field(
        max_length=JIT_BACKEND_MAX_LENGTH,
        pattern=JIT_BACKEND_PATTERN,
    )


###############################################################################
class SettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: SettingsJobsResponse
    device: SettingsDeviceResponse

    # -------------------------------------------------------------------------
    @classmethod
    def from_json_settings(cls, settings: JsonServerSettings) -> "SettingsResponse":
        return cls(
            jobs=SettingsJobsResponse(
                polling_interval=settings.jobs.polling_interval,
            ),
            device=SettingsDeviceResponse(
                jit_compile=settings.device.jit_compile,
                jit_backend=settings.device.jit_backend,
            ),
        )
