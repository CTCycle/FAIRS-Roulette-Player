from __future__ import annotations

from FAIRS.server.configurations.server import build_database_settings


def test_database_settings_use_json_payload_for_embedded_mode() -> None:
    payload = {
        "embedded_database": True,
        "connect_timeout": 25,
        "insert_batch_size": 250,
    }

    settings = build_database_settings(payload)

    assert settings.embedded_database is True
    assert settings.engine is None
    assert settings.host is None
    assert settings.database_name is None
    assert settings.connect_timeout == 25
    assert settings.insert_batch_size == 250


def test_database_settings_use_json_payload_for_external_postgres_mode() -> None:
    payload = {
        "embedded_database": False,
        "engine": "postgresql+psycopg",
        "host": "json-host",
        "port": 6543,
        "database_name": "json-db",
        "username": "json-user",
        "password": "json-pass",
        "ssl": True,
        "ssl_ca": "/tmp/ca.pem",
        "connect_timeout": 25,
        "insert_batch_size": 250,
    }

    settings = build_database_settings(payload)

    assert settings.embedded_database is False
    assert settings.engine == "postgresql+psycopg"
    assert settings.host == "json-host"
    assert settings.port == 6543
    assert settings.database_name == "json-db"
    assert settings.username == "json-user"
    assert settings.password == "json-pass"
    assert settings.ssl is True
    assert settings.ssl_ca == "/tmp/ca.pem"
    assert settings.connect_timeout == 25
    assert settings.insert_batch_size == 250


def test_database_settings_ignore_db_env_overrides(monkeypatch) -> None:
    payload = {
        "embedded_database": False,
        "engine": "postgres",
        "host": "json-host",
        "port": 5432,
        "database_name": "json-db",
        "username": "json-user",
        "password": "json-pass",
        "ssl": False,
        "ssl_ca": None,
        "connect_timeout": 10,
        "insert_batch_size": 1000,
    }
    monkeypatch.setenv("DB_EMBEDDED", "true")
    monkeypatch.setenv("DB_ENGINE", "postgresql+psycopg")
    monkeypatch.setenv("DB_HOST", "env-host")
    monkeypatch.setenv("DB_PORT", "7000")
    monkeypatch.setenv("DB_NAME", "env-db")
    monkeypatch.setenv("DB_USER", "env-user")
    monkeypatch.setenv("DB_PASSWORD", "env-pass")
    monkeypatch.setenv("DB_SSL", "true")
    monkeypatch.setenv("DB_SSL_CA", "/tmp/env-ca.pem")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "99")
    monkeypatch.setenv("DB_INSERT_BATCH_SIZE", "9999")

    settings = build_database_settings(payload)

    assert settings.embedded_database is False
    assert settings.engine == "postgres"
    assert settings.host == "json-host"
    assert settings.port == 5432
    assert settings.database_name == "json-db"
    assert settings.username == "json-user"
    assert settings.password == "json-pass"
    assert settings.ssl is False
    assert settings.ssl_ca is None
    assert settings.connect_timeout == 10
    assert settings.insert_batch_size == 1000
