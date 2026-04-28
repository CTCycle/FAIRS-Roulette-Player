from __future__ import annotations

import os
import urllib.parse
import sqlalchemy
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from FAIRS.server.configurations import DatabaseSettings
from FAIRS.server.configurations.startup import get_server_settings
from FAIRS.server.common.constants import DATABASE_FILENAME, RESOURCES_PATH
from FAIRS.server.common.utils.logger import logger
from FAIRS.server.repositories.database.postgres import PostgresRepository
from FAIRS.server.repositories.database.sqlite import SQLiteRepository
from FAIRS.server.repositories.database.utils import normalize_postgres_engine
from FAIRS.server.repositories.schemas.models import Base, RouletteOutcomes


ROULETTE_POSITION_MAP: dict[int, int] = {
    0: 0,
    32: 1,
    15: 2,
    19: 3,
    4: 4,
    21: 5,
    2: 6,
    25: 7,
    17: 8,
    34: 9,
    6: 10,
    27: 11,
    13: 12,
    36: 13,
    11: 14,
    30: 15,
    8: 16,
    23: 17,
    10: 18,
    5: 19,
    24: 20,
    16: 21,
    33: 22,
    1: 23,
    20: 24,
    14: 25,
    31: 26,
    9: 27,
    22: 28,
    18: 29,
    29: 30,
    7: 31,
    28: 32,
    12: 33,
    35: 34,
    3: 35,
    26: 36,
}

ROULETTE_COLOR_MAP: dict[str, list[int]] = {
    "black": [
        15,
        4,
        2,
        17,
        6,
        13,
        11,
        8,
        10,
        24,
        33,
        20,
        31,
        22,
        29,
        28,
        35,
        26,
    ],
    "red": [
        32,
        19,
        21,
        25,
        34,
        27,
        36,
        30,
        23,
        5,
        16,
        1,
        14,
        9,
        18,
        7,
        12,
        3,
    ],
    "green": [0],
}

ROULETTE_COLOR_CODE = {"green": 0, "black": 1, "red": 2}


###############################################################################
def build_postgres_connect_args(settings: DatabaseSettings) -> dict[str, str | int]:
    connect_args: dict[str, str | int] = {"connect_timeout": settings.connect_timeout}
    if settings.ssl:
        connect_args["sslmode"] = "require"
        if settings.ssl_ca:
            connect_args["sslrootcert"] = settings.ssl_ca
    return connect_args


# -----------------------------------------------------------------------------
def build_postgres_url(settings: DatabaseSettings, database_name: str) -> str:
    port = settings.port or 5432
    engine_name = normalize_postgres_engine(settings.engine)
    safe_username = urllib.parse.quote_plus(settings.username or "")
    safe_password = urllib.parse.quote_plus(settings.password or "")
    return (
        f"{engine_name}://{safe_username}:{safe_password}"
        f"@{settings.host}:{port}/{database_name}"
    )


# -----------------------------------------------------------------------------
def escape_postgres_identifier(identifier: str) -> str:
    return identifier.replace('"', '""')


# -----------------------------------------------------------------------------
def is_missing_postgres_database_error(
    exc: SQLAlchemyError,
    target_database: str,
) -> bool:
    original = getattr(exc, "orig", None)
    sql_state = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    if sql_state == "3D000":
        return True
    lowered = str(exc).lower()
    return "does not exist" in lowered and target_database.lower() in lowered


# -----------------------------------------------------------------------------
def postgres_database_exists(
    settings: DatabaseSettings,
    target_database: str,
    connect_args: dict[str, str | int],
) -> bool:
    probe_engine = sqlalchemy.create_engine(
        build_postgres_url(settings, target_database),
        echo=False,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    try:
        with probe_engine.connect():
            return True
    except SQLAlchemyError as exc:
        if is_missing_postgres_database_error(exc, target_database):
            return False
        raise
    finally:
        probe_engine.dispose()


# -----------------------------------------------------------------------------
def initialize_sqlite_database(settings: DatabaseSettings) -> None:
    repository = SQLiteRepository(settings, initialize_schema=True)
    seed_roulette_outcomes(repository.engine)
    logger.info("Initialized SQLite database at %s", repository.db_path)


def initialize_sqlite_database_if_missing(settings: DatabaseSettings) -> None:
    db_path = os.path.join(RESOURCES_PATH, DATABASE_FILENAME)
    if os.path.exists(db_path):
        return
    initialize_sqlite_database(settings)


# -----------------------------------------------------------------------------
def initialize_sqlite_on_startup_if_missing() -> None:
    settings = get_server_settings().database
    if not settings.embedded_database:
        return
    initialize_sqlite_database_if_missing(settings)


# -----------------------------------------------------------------------------
def ensure_postgres_database(settings: DatabaseSettings) -> str:
    if not settings.host:
        raise ValueError("Database host is required for PostgreSQL initialization.")
    if not settings.username:
        raise ValueError("Database username is required for PostgreSQL initialization.")
    if not settings.database_name:
        raise ValueError("Database name is required for PostgreSQL initialization.")

    target_database = settings.database_name
    connect_args = build_postgres_connect_args(settings)

    admin_url = build_postgres_url(settings, "postgres")
    admin_engine = sqlalchemy.create_engine(
        admin_url,
        echo=False,
        future=True,
        connect_args=connect_args,
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )
    try:
        exists = postgres_database_exists(settings, target_database, connect_args)
        if exists:
            logger.info("PostgreSQL database %s already exists", target_database)
        else:
            safe_database_name = escape_postgres_identifier(target_database)
            create_database_stmt = (
                f'CREATE DATABASE "{safe_database_name}" '
                "WITH ENCODING 'UTF8' TEMPLATE template0"
            )
            with admin_engine.connect() as conn:
                conn.exec_driver_sql(create_database_stmt)
            logger.info("Created PostgreSQL database %s", target_database)
    finally:
        admin_engine.dispose()

    normalized_settings = DatabaseSettings(
        embedded_database=False,
        engine=settings.engine,
        host=settings.host,
        port=settings.port,
        database_name=target_database,
        username=settings.username,
        password=settings.password,
        ssl=settings.ssl,
        ssl_ca=settings.ssl_ca,
        connect_timeout=settings.connect_timeout,
        insert_batch_size=settings.insert_batch_size,
    )
    repository = PostgresRepository(normalized_settings)
    Base.metadata.create_all(repository.engine)
    seed_roulette_outcomes(repository.engine)
    logger.info("Ensured PostgreSQL tables exist in %s", target_database)

    return target_database


# -----------------------------------------------------------------------------
def run_database_initialization() -> None:
    settings = get_server_settings().database
    if settings.embedded_database:
        initialize_sqlite_database(settings)
        return

    engine_name = normalize_postgres_engine(settings.engine).lower()
    if engine_name not in {
        "postgres",
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
    }:
        raise ValueError(f"Unsupported database engine: {settings.engine}")

    ensure_postgres_database(settings)


# -----------------------------------------------------------------------------
def build_roulette_outcome_seed_rows() -> list[dict[str, int | str]]:
    reverse_color_map = {
        number: color
        for color, numbers in ROULETTE_COLOR_MAP.items()
        for number in numbers
    }
    rows: list[dict[str, int | str]] = []
    for outcome_id in range(37):
        color = reverse_color_map.get(outcome_id)
        wheel_position = ROULETTE_POSITION_MAP.get(outcome_id)
        color_code = ROULETTE_COLOR_CODE.get(color or "")
        if color is None or wheel_position is None or color_code is None:
            raise ValueError(f"Incomplete roulette mapping for outcome {outcome_id}")
        rows.append(
            {
                "outcome_id": outcome_id,
                "color": color,
                "color_code": color_code,
                "wheel_position": wheel_position,
            }
        )
    return rows

# -----------------------------------------------------------------------------
def seed_roulette_outcomes(engine: sqlalchemy.Engine) -> None:
    inspector = sqlalchemy.inspect(engine)
    if not inspector.has_table("roulette_outcomes"):
        return
    rows = build_roulette_outcome_seed_rows()
    session_factory = sessionmaker(bind=engine, future=True)
    session = session_factory()
    try:
        current = session.scalar(select(func.count()).select_from(RouletteOutcomes)) or 0
        if int(current) == len(rows):
            return
        session.execute(delete(RouletteOutcomes))
        session.add_all([RouletteOutcomes(**row) for row in rows])
        session.commit()
    finally:
        session.close()
    logger.info("Seeded roulette_outcomes table with %d rows", len(rows))


# -----------------------------------------------------------------------------
def initialize_database() -> None:
    try:
        run_database_initialization()
    except (SQLAlchemyError, ValueError) as exc:
        logger.error("Database initialization failed: %s", exc)
        raise SystemExit(1) from exc
    except Exception as exc:
        logger.exception("Unexpected error during database initialization.")
        raise SystemExit(1) from exc
