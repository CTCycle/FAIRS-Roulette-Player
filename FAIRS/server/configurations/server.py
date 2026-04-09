from __future__ import annotations

from typing import Any

from FAIRS.server.configurations.base import ensure_mapping
from FAIRS.server.configurations.settings import (
    JsonDatabaseSettings,
    JsonDeviceSettings,
    JsonJobsSettings,
    get_app_settings,
    get_server_settings,
)
from FAIRS.server.domain.configuration import (
    DatabaseSettings,
    DeviceSettings,
    JobsSettings,
    ServerSettings,
)


###############################################################################
def build_database_settings(payload: dict[str, Any] | Any) -> DatabaseSettings:
    data = ensure_mapping(payload)
    db = JsonDatabaseSettings.model_validate(data)
    if db.embedded_database:
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
            connect_timeout=db.connect_timeout,
            insert_batch_size=db.insert_batch_size,
        )

    return DatabaseSettings(
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


# -----------------------------------------------------------------------------
def build_jobs_settings(payload: dict[str, Any] | Any) -> JobsSettings:
    data = ensure_mapping(payload)
    jobs = JsonJobsSettings.model_validate(data)
    return JobsSettings(polling_interval=jobs.polling_interval)


# -----------------------------------------------------------------------------
def build_device_settings(payload: dict[str, Any] | Any) -> DeviceSettings:
    data = ensure_mapping(payload)
    device = JsonDeviceSettings.model_validate(data)
    return DeviceSettings(
        jit_compile=device.jit_compile,
        jit_backend=device.jit_backend,
        use_mixed_precision=device.use_mixed_precision,
    )


# -----------------------------------------------------------------------------
def build_server_settings(data: dict[str, Any] | Any) -> ServerSettings:
    payload = ensure_mapping(data)
    return ServerSettings(
        database=build_database_settings(payload.get("database")),
        jobs=build_jobs_settings(payload.get("jobs")),
        device=build_device_settings(payload.get("device")),
    )


# [POLLING HELPERS]
###############################################################################
def get_poll_interval_seconds(
    settings: ServerSettings | None = None,
    minimum: float = 0.25,
) -> float:
    resolved = settings or server_settings
    value = float(resolved.jobs.polling_interval)
    return max(minimum, value)


server_settings = get_server_settings()
app_settings = get_app_settings()

