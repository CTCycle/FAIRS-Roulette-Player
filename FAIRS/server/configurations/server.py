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
class FastAPISettings:
    title: str
    description: str
    version: str   

# -----------------------------------------------------------------------------
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
    fetch_row_limit: int

# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class TrainingSettings:
    polling_interval: float
    default_episodes: int
    default_max_steps_episode: int
    default_render_update_frequency: int
    render_environment: bool

# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class DeviceSettings:
    jit_compile: bool
    jit_backend: str
    use_mixed_precision: bool

# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class ServerSettings:
    fastapi: FastAPISettings
    database: DatabaseSettings
    training: TrainingSettings
    device: DeviceSettings     


# [BUILDER FUNCTIONS]
###############################################################################
def build_fastapi_settings(data: dict[str, Any]) -> FastAPISettings:
    payload = ensure_mapping(data)
    return FastAPISettings(
        title=coerce_str(payload.get("title"), "FAIRS Roulette Backend"),
        version=coerce_str(payload.get("version"), "0.1.0"),
        description=coerce_str(payload.get("description"), "FastAPI backend"),        
    )

# -----------------------------------------------------------------------------
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
            fetch_row_limit=coerce_int(payload.get("fetch_row_limit"), 100, minimum=10),
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
        fetch_row_limit=coerce_int(payload.get("fetch_row_limit"), 100, minimum=10),
    )

# -----------------------------------------------------------------------------
def build_training_settings(payload: dict[str, Any] | Any) -> TrainingSettings:
    data = ensure_mapping(payload)
    return TrainingSettings(
        polling_interval=coerce_float(
            data.get("polling_interval"), 1.0, minimum=0.1, maximum=10.0
        ),
        default_episodes=coerce_int(
            data.get("default_episodes"), 10, minimum=1
        ),
        default_max_steps_episode=coerce_int(
            data.get("default_max_steps_episode"), 2000, minimum=100
        ),
        default_render_update_frequency=coerce_int(
            data.get("default_render_update_frequency"), 20, minimum=1
        ),
        render_environment=coerce_bool(data.get("render_environment"), False),
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
    fastapi_payload = ensure_mapping(payload.get("fastapi"))
    database_payload = ensure_mapping(payload.get("database"))
    training_payload = ensure_mapping(payload.get("training"))
    device_payload = ensure_mapping(payload.get("device"))
  
    return ServerSettings(
        fastapi=build_fastapi_settings(fastapi_payload),
        database=build_database_settings(database_payload),
        training=build_training_settings(training_payload),
        device=build_device_settings(device_payload),
    )


# [SERVER CONFIGURATION LOADER]
###############################################################################
def get_server_settings(config_path: str | None = None) -> ServerSettings:
    path = config_path or CONFIGURATIONS_FILE
    payload = load_configuration_data(path)
    
    return build_server_settings(payload)


server_settings = get_server_settings()
