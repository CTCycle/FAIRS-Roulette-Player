from __future__ import annotations

import os
from typing import Any

from FAIRS.server.configurations.base import ensure_mapping, load_configuration_data
from FAIRS.server.entities.configuration import (
    DatabaseSettings,
    DeviceSettings,
    JobsSettings,
    ServerSettings,
)

from FAIRS.server.common.constants import (
    CONFIGURATIONS_FILE,
)

from FAIRS.server.common.utils.types import (
    coerce_bool,
    coerce_float,
    coerce_int,
    coerce_str,
    coerce_str_or_none,
)


# [BUILDER FUNCTIONS]
###############################################################################
def _read_env_value(env_key: str, payload: dict[str, Any], payload_key: str) -> Any:
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value
    return payload.get(payload_key)


# -----------------------------------------------------------------------------
def build_database_settings(payload: dict[str, Any] | Any) -> DatabaseSettings:
    data = ensure_mapping(payload)

    embedded_raw = _read_env_value("DB_EMBEDDED", data, "embedded_database")
    embedded = coerce_bool(embedded_raw, True)
    if embedded:
        # External fields are ignored entirely when embedded DB is active
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
            connect_timeout=coerce_int(
                _read_env_value("DB_CONNECT_TIMEOUT", data, "connect_timeout"),
                10,
                minimum=1,
            ),
            insert_batch_size=coerce_int(
                _read_env_value("DB_INSERT_BATCH_SIZE", data, "insert_batch_size"),
                1000,
                minimum=1,
            ),
        )

    # External DB mode
    engine_value = (
        coerce_str_or_none(_read_env_value("DB_ENGINE", data, "engine")) or "postgres"
    )
    normalized_engine = engine_value.lower() if engine_value else None
    return DatabaseSettings(
        embedded_database=False,
        engine=normalized_engine,
        host=coerce_str_or_none(_read_env_value("DB_HOST", data, "host")),
        port=coerce_int(
            _read_env_value("DB_PORT", data, "port"),
            5432,
            minimum=1,
            maximum=65535,
        ),
        database_name=coerce_str_or_none(
            _read_env_value("DB_NAME", data, "database_name")
        ),
        username=coerce_str_or_none(_read_env_value("DB_USER", data, "username")),
        password=coerce_str_or_none(_read_env_value("DB_PASSWORD", data, "password")),
        ssl=coerce_bool(_read_env_value("DB_SSL", data, "ssl"), False),
        ssl_ca=coerce_str_or_none(_read_env_value("DB_SSL_CA", data, "ssl_ca")),
        connect_timeout=coerce_int(
            _read_env_value("DB_CONNECT_TIMEOUT", data, "connect_timeout"),
            10,
            minimum=1,
        ),
        insert_batch_size=coerce_int(
            _read_env_value("DB_INSERT_BATCH_SIZE", data, "insert_batch_size"),
            1000,
            minimum=1,
        ),
    )


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def build_jobs_settings(payload: dict[str, Any] | Any) -> JobsSettings:
    data = ensure_mapping(payload)
    return JobsSettings(
        polling_interval=coerce_float(
            data.get("polling_interval"), 1.0, minimum=0.1, maximum=10.0
        ),
    )


# -----------------------------------------------------------------------------
def build_device_settings(payload: dict[str, Any] | Any) -> DeviceSettings:
    data = ensure_mapping(payload)
    return DeviceSettings(
        jit_compile=coerce_bool(data.get("jit_compile"), False),
        jit_backend=coerce_str(data.get("jit_backend"), "inductor"),
        use_mixed_precision=coerce_bool(data.get("use_mixed_precision"), False),
    )


# -----------------------------------------------------------------------------
def build_server_settings(data: dict[str, Any] | Any) -> ServerSettings:
    payload = ensure_mapping(data)
    database_payload = ensure_mapping(payload.get("database"))
    jobs_payload = ensure_mapping(payload.get("jobs"))
    device_payload = ensure_mapping(payload.get("device"))

    return ServerSettings(
        database=build_database_settings(database_payload),
        jobs=build_jobs_settings(jobs_payload),
        device=build_device_settings(device_payload),
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


# [SERVER CONFIGURATION LOADER]
###############################################################################
def get_server_settings(config_path: str | None = None) -> ServerSettings:
    path = config_path or CONFIGURATIONS_FILE
    payload = load_configuration_data(path)

    return build_server_settings(payload)


server_settings = get_server_settings()
