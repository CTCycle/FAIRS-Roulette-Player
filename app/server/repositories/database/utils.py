from __future__ import annotations

from typing import Any

from server.configurations import DatabaseSettings


###############################################################################
def build_postgres_connect_args(settings: DatabaseSettings) -> dict[str, Any]:
    connect_args: dict[str, Any] = {"connect_timeout": settings.connect_timeout}
    if settings.ssl:
        connect_args["sslmode"] = "require"
        if settings.ssl_ca:
            connect_args["sslrootcert"] = settings.ssl_ca
    return connect_args


SUPPORTED_POSTGRES_ENGINES = frozenset({"postgresql+psycopg"})


###############################################################################
def is_supported_postgres_engine(engine: str | None) -> bool:
    return bool(engine) and engine.strip().lower() in SUPPORTED_POSTGRES_ENGINES
