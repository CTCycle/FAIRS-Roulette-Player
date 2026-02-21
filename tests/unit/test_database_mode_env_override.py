from __future__ import annotations

from FAIRS.server.configurations.server import build_database_settings


def test_db_embedded_env_overrides_json_defaults(monkeypatch) -> None:
    payload = {
        "embedded_database": False,
        "engine": "postgres",
        "host": "json-host",
    }
    monkeypatch.setenv("DB_EMBEDDED", "true")

    settings = build_database_settings(payload)

    assert settings.embedded_database is True
    assert settings.engine is None
    assert settings.host is None
    assert settings.database_name is None


def test_external_db_env_fields_are_used_when_embedded_disabled(monkeypatch) -> None:
    payload = {
        "embedded_database": True,
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
    monkeypatch.setenv("DB_EMBEDDED", "false")
    monkeypatch.setenv("DB_ENGINE", "postgresql+psycopg")
    monkeypatch.setenv("DB_HOST", "env-host")
    monkeypatch.setenv("DB_PORT", "6543")
    monkeypatch.setenv("DB_NAME", "env-db")
    monkeypatch.setenv("DB_USER", "env-user")
    monkeypatch.setenv("DB_PASSWORD", "env-pass")
    monkeypatch.setenv("DB_SSL", "true")
    monkeypatch.setenv("DB_SSL_CA", "/tmp/ca.pem")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "25")
    monkeypatch.setenv("DB_INSERT_BATCH_SIZE", "250")

    settings = build_database_settings(payload)

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
