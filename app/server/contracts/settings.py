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
class SettingsRoulettePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_number: int | None = Field(
        default=None,
        ge=0,
        le=36,
        description="Minimum roulette outcome included in the active number pool.",
    )
    maximum_number: int | None = Field(
        default=None,
        ge=0,
        le=36,
        description="Maximum roulette outcome included in the active number pool.",
    )
    exclude_zero: bool | None = Field(
        default=None,
        description="Whether zero is removed from the active roulette number pool.",
    )
    invert_colors: bool | None = Field(
        default=None,
        description="Whether red and black wheel colors are inverted for visualization.",
    )
    show_number_labels: bool | None = Field(
        default=None,
        description="Whether roulette wheel visualization renders number labels.",
    )

    # -------------------------------------------------------------------------
    @model_validator(mode="after")
    def validate_patch(self) -> "SettingsRoulettePatch":
        for field_name in (
            "minimum_number",
            "maximum_number",
            "exclude_zero",
            "invert_colors",
            "show_number_labels",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null.")
        if (
            self.minimum_number is not None
            and self.maximum_number is not None
            and self.minimum_number > self.maximum_number
        ):
            raise ValueError("minimum_number must be less than or equal to maximum_number.")
        return self

###############################################################################
class SettingsPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: SettingsJobsPatch | None = None
    device: SettingsDevicePatch | None = None
    roulette: SettingsRoulettePatch | None = None

    # -------------------------------------------------------------------------
    @model_validator(mode="after")
    def reject_explicit_null_blocks(self) -> "SettingsPatchRequest":
        if "jobs" in self.model_fields_set and self.jobs is None:
            raise ValueError("jobs must be an object.")
        if "device" in self.model_fields_set and self.device is None:
            raise ValueError("device must be an object.")
        if "roulette" in self.model_fields_set and self.roulette is None:
            raise ValueError("roulette must be an object.")
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
class SettingsRouletteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_number: int = Field(ge=0, le=36)
    maximum_number: int = Field(ge=0, le=36)
    exclude_zero: bool
    invert_colors: bool
    show_number_labels: bool

###############################################################################
class SettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: SettingsJobsResponse
    device: SettingsDeviceResponse
    roulette: SettingsRouletteResponse

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
            roulette=SettingsRouletteResponse(
                minimum_number=settings.roulette.minimum_number,
                maximum_number=settings.roulette.maximum_number,
                exclude_zero=settings.roulette.exclude_zero,
                invert_colors=settings.roulette.invert_colors,
                show_number_labels=settings.roulette.show_number_labels,
            ),
        )
