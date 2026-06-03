from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.domain.configuration import EnvDatabaseSettings, JsonServerSettings

DATABASE_ENV_KEYS = (
    "EMBEDDED_DATABASE",
    "DATABASE_URL",
    "DATABASE_ENGINE",
    "DATABASE_HOST",
    "DATABASE_PORT",
    "DATABASE_NAME",
    "DATABASE_USERNAME",
    "DATABASE_PASSWORD",
    "DATABASE_SSL",
    "DATABASE_SSL_CA",
    "DATABASE_CONNECT_TIMEOUT",
    "DATABASE_INSERT_BATCH_SIZE",
)


@pytest.fixture(autouse=True)
def reset_database_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in DATABASE_ENV_KEYS:
        monkeypatch.delenv(env_name, raising=False)


def test_database_settings_use_env_payload_for_embedded_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMBEDDED_DATABASE", "true")
    monkeypatch.setenv("DATABASE_CONNECT_TIMEOUT", "25")
    monkeypatch.setenv("DATABASE_INSERT_BATCH_SIZE", "250")

    settings = JsonServerSettings.model_validate({}).to_server_settings().database

    assert settings.embedded_database is True
    assert settings.engine is None
    assert settings.host is None
    assert settings.database_name is None
    assert settings.connect_timeout == 25
    assert settings.insert_batch_size == 250


def test_database_settings_use_env_payload_for_external_postgres_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMBEDDED_DATABASE", "false")
    monkeypatch.setenv("DATABASE_ENGINE", "postgresql+psycopg")
    monkeypatch.setenv("DATABASE_HOST", "env-host")
    monkeypatch.setenv("DATABASE_PORT", "6543")
    monkeypatch.setenv("DATABASE_NAME", "env-db")
    monkeypatch.setenv("DATABASE_USERNAME", "env-user")
    monkeypatch.setenv("DATABASE_PASSWORD", "env-pass")
    monkeypatch.setenv("DATABASE_SSL", "true")
    monkeypatch.setenv("DATABASE_SSL_CA", "/tmp/ca.pem")
    monkeypatch.setenv("DATABASE_CONNECT_TIMEOUT", "25")
    monkeypatch.setenv("DATABASE_INSERT_BATCH_SIZE", "250")

    settings = JsonServerSettings.model_validate({}).to_server_settings().database

    assert settings.embedded_database is False
    assert settings.engine == "postgresql+psycopg"
    assert settings.host == "env-host"
    assert settings.port == 6543
    assert settings.database_name == "env-db"
    assert settings.username == "env-user"
    assert settings.password == "env-pass"
    assert settings.ssl is True
    assert settings.ssl_ca == "/tmp/ca.pem"
    assert settings.connect_timeout == 25
    assert settings.insert_batch_size == 250


def test_database_settings_parse_database_url_and_allow_explicit_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://url-user:url-pass@url-host:5544/url-db",
    )
    monkeypatch.setenv("EMBEDDED_DATABASE", "false")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("DATABASE_USERNAME", "override-user")

    settings = JsonServerSettings.model_validate({}).to_server_settings().database

    assert settings.embedded_database is False
    assert settings.engine == "postgresql+psycopg"
    assert settings.host == "url-host"
    assert settings.port == 5432
    assert settings.database_name == "url-db"
    assert settings.username == "override-user"
    assert settings.password == "url-pass"
    assert settings.ssl is False
    assert settings.ssl_ca is None
    assert settings.connect_timeout == 10
    assert settings.insert_batch_size == 1000


def test_database_validation_requires_external_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(
        ValidationError, match="database.host, database.database_name, database.username"
    ):
        monkeypatch.setenv("EMBEDDED_DATABASE", "false")
        _ = EnvDatabaseSettings.from_environment()
