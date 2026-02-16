from __future__ import annotations

import urllib.parse

import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError

from FAIRS.server.configurations import DatabaseSettings, server_settings
from FAIRS.server.common.utils.logger import logger
from FAIRS.server.repositories.database.postgres import PostgresRepository
from FAIRS.server.repositories.database.sqlite import SQLiteRepository
from FAIRS.server.repositories.database.utils import normalize_postgres_engine
from FAIRS.server.repositories.schemas.models import Base


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
def clone_settings_with_database(
    settings: DatabaseSettings, database_name: str
) -> DatabaseSettings:
    return DatabaseSettings(
        embedded_database=False,
        engine=settings.engine,
        host=settings.host,
        port=settings.port,
        database_name=database_name,
        username=settings.username,
        password=settings.password,
        ssl=settings.ssl,
        ssl_ca=settings.ssl_ca,
        connect_timeout=settings.connect_timeout,
        insert_batch_size=settings.insert_batch_size,
    )


# -----------------------------------------------------------------------------
def initialize_sqlite_database(settings: DatabaseSettings) -> None:
    repository = SQLiteRepository(settings)
    seed_roulette_outcomes(repository.engine)
    logger.info("Initialized SQLite database at %s", repository.db_path)


# -----------------------------------------------------------------------------
def ensure_postgres_database(settings: DatabaseSettings) -> str:
    if not settings.host:
        raise ValueError("Database host is required for PostgreSQL initialization.")
    if not settings.username:
        raise ValueError("Database username is required for PostgreSQL initialization.")
    if not settings.database_name:
        raise ValueError("Database name is required for PostgreSQL initialization.")

    target_database = settings.database_name
    safe_database = target_database.replace('"', '""')
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

    with admin_engine.connect() as conn:
        exists = conn.execute(
            sqlalchemy.text("SELECT 1 FROM pg_database WHERE datname=:name"),
            {"name": target_database},
        ).scalar()
        if exists:
            logger.info("PostgreSQL database %s already exists", target_database)
        else:
            conn.execute(
                sqlalchemy.text(
                    f'CREATE DATABASE "{safe_database}" WITH ENCODING \'UTF8\''
                )
            )
            logger.info("Created PostgreSQL database %s", target_database)

    normalized_settings = clone_settings_with_database(settings, target_database)
    repository = PostgresRepository(normalized_settings)
    Base.metadata.create_all(repository.engine)
    seed_roulette_outcomes(repository.engine)
    logger.info("Ensured PostgreSQL tables exist in %s", target_database)

    return target_database


# -----------------------------------------------------------------------------
def run_database_initialization() -> None:
    settings = server_settings.database
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
    with engine.begin() as conn:
        current = (
            conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM roulette_outcomes")
            ).scalar()
            or 0
        )
        if int(current) == len(rows):
            return
        conn.execute(sqlalchemy.text("DELETE FROM roulette_outcomes"))
        insert_stmt = sqlalchemy.text(
            "INSERT INTO roulette_outcomes "
            "(outcome_id, color, color_code, wheel_position) "
            "VALUES (:outcome_id, :color, :color_code, :wheel_position)"
        )
        conn.execute(insert_stmt, rows)
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
