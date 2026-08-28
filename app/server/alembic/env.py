from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
import sys
from typing import Any

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from server.common import path as shared_paths  # noqa: E402
from server.configurations.startup import get_server_settings  # noqa: E402
from server.repositories.database.initializer import build_postgres_url  # noqa: E402
from server.repositories.schemas.models import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
VERSION_TABLE = "alembic_version"

###############################################################################
def _include_object(
    _object: Any,
    name: str,
    object_type: str,
    _reflected: bool,
    _compare_to: Any,
) -> bool:
    return not (object_type == "table" and name == VERSION_TABLE)

###############################################################################
def _resolved_url() -> str:
    configured = (config.get_main_option("sqlalchemy.url") or "").strip()
    if configured:
        return configured

    settings = get_server_settings().database
    if settings.embedded_database:
        return f"sqlite:///{shared_paths.DATABASE_PATH}"
    if not settings.database_name:
        raise RuntimeError("DATABASE_NAME is required for PostgreSQL Alembic commands.")
    return str(build_postgres_url(settings, settings.database_name))

###############################################################################
def _configure_kwargs(connection: Any | None = None) -> dict[str, Any]:
    dialect_name = connection.dialect.name if connection is not None else make_url(_resolved_url()).get_backend_name()
    return {
        "target_metadata": target_metadata,
        "compare_type": True,
        "compare_server_default": True,
        "include_object": _include_object,
        "render_as_batch": dialect_name == "sqlite",
        "transactional_ddl": True,
        "transaction_per_migration": False,
    }

###############################################################################
def run_migrations_offline() -> None:
    context.configure(
        url=_resolved_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_configure_kwargs(),
    )
    with context.begin_transaction():
        context.run_migrations()

###############################################################################
def run_migrations_online() -> None:
    connectable = config.attributes.get("connection")
    owns_connectable = connectable is None
    if connectable is None:
        url = _resolved_url()
        parsed_url = make_url(url)
        connect_args = {"autocommit": False} if parsed_url.get_backend_name() == "sqlite" else {}
        connectable = create_engine(
            url,
            future=True,
            poolclass=NullPool,
            connect_args=connect_args,
        )

    try:
        if owns_connectable:
            with connectable.connect() as connection:
                context.configure(connection=connection, **_configure_kwargs(connection))
                with context.begin_transaction():
                    context.run_migrations()
        else:
            context.configure(connection=connectable, **_configure_kwargs(connectable))
            with context.begin_transaction():
                context.run_migrations()
    finally:
        if owns_connectable:
            connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
