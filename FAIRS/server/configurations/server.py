from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from FAIRS.server.configurations.base import (
    ensure_mapping, 
    load_configuration_data    
)

from FAIRS.server.utils.constants import (
    CONFIGURATIONS_FILE,
)

from FAIRS.server.utils.types import (
    coerce_bool,
    coerce_float,
    coerce_int,
    coerce_str,
    coerce_str_or_none,
)




# [SERVER SETTINGS]
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
    browse_batch_size: int

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class JobsSettings:
    polling_interval: float

# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class DeviceSettings:
    jit_compile: bool
    jit_backend: str
    use_mixed_precision: bool

# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class ServerSettings:
    database: DatabaseSettings
    jobs: JobsSettings
    device: DeviceSettings     


# [BUILDER FUNCTIONS]
###############################################################################
def build_database_settings(payload: dict[str, Any] | Any) -> DatabaseSettings:
    embedded = bool(payload.get("embedded_database", True))
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
            connect_timeout=10,
            insert_batch_size=coerce_int(payload.get("insert_batch_size"), 1000, minimum=1),
            browse_batch_size=coerce_int(payload.get("browse_batch_size"), 200, minimum=10),
        )

    # External DB mode
    engine_value = coerce_str_or_none(payload.get("engine")) or "postgres"
    normalized_engine = engine_value.lower() if engine_value else None
    return DatabaseSettings(
        embedded_database=False,
        engine=normalized_engine,
        host=coerce_str_or_none(payload.get("host")),
        port=coerce_int(payload.get("port"), 5432, minimum=1, maximum=65535),
        database_name=coerce_str_or_none(payload.get("database_name")),
        username=coerce_str_or_none(payload.get("username")),
        password=coerce_str_or_none(payload.get("password")),
        ssl=bool(payload.get("ssl", False)),
        ssl_ca=coerce_str_or_none(payload.get("ssl_ca")),
        connect_timeout=coerce_int(payload.get("connect_timeout"), 10, minimum=1),
        insert_batch_size=coerce_int(payload.get("insert_batch_size"), 1000, minimum=1),
        browse_batch_size=coerce_int(payload.get("browse_batch_size"), 200, minimum=10),
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


# [SERVER CONFIGURATION LOADER]
###############################################################################
def get_server_settings(config_path: str | None = None) -> ServerSettings:
    path = config_path or CONFIGURATIONS_FILE
    payload = load_configuration_data(path)
    
    return build_server_settings(payload)


server_settings = get_server_settings()
