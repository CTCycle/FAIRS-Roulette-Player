from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

import pytest

from server.configurations import environment, startup


###############################################################################
@pytest.fixture(autouse=True)
def reset_configuration_state() -> None:
    startup.get_configuration_manager.cache_clear()
    environment.reset_environment_for_tests()
    yield
    startup.get_configuration_manager.cache_clear()
    environment.reset_environment_for_tests()


# -----------------------------------------------------------------------------
def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


# -----------------------------------------------------------------------------
def _write_env(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# -----------------------------------------------------------------------------
def _default_json_config() -> dict[str, object]:
    return {
        "database": {
            "embedded_database": False,
            "engine": "postgres",
            "host": "json-db",
            "port": 5432,
            "database_name": "json_name",
            "username": "json_user",
            "password": "json_pass",
            "ssl": False,
            "ssl_ca": None,
            "connect_timeout": 10,
            "insert_batch_size": 1000,
        },
        "jobs": {"polling_interval": 1.0},
        "device": {"jit_compile": False, "jit_backend": "inductor", "use_mixed_precision": False},
    }


# -----------------------------------------------------------------------------
def test_environment_overrides_existing_process_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=from_dotenv"])

    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))
    monkeypatch.setenv("FASTAPI_HOST", "from_process")

    environment.load_environment()

    assert os.getenv("FASTAPI_HOST") == "from_dotenv"


# -----------------------------------------------------------------------------
def test_environment_load_is_idempotent_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=first"])

    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))

    environment.load_environment()
    _write_env(env_path, ["FASTAPI_HOST=second"])
    environment.load_environment()

    assert os.getenv("FASTAPI_HOST") == "first"


# -----------------------------------------------------------------------------
def test_environment_force_reload_applies_updated_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=first"])
    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))

    environment.load_environment()
    _write_env(env_path, ["FASTAPI_HOST=second"])
    environment.load_environment(force=True)

    assert os.getenv("FASTAPI_HOST") == "second"


# -----------------------------------------------------------------------------
def test_server_package_import_loads_environment_early(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["KERAS_BACKEND=torch"])

    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))
    monkeypatch.setenv("KERAS_BACKEND", "tensorflow")

    import server as server_package

    importlib.reload(server_package)

    assert os.getenv("KERAS_BACKEND") == "torch"


# -----------------------------------------------------------------------------
def test_server_settings_use_json_configuration_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    _write_json(config_path, _default_json_config())

    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=127.0.0.1"])
    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))

    settings = startup.reload_settings_for_tests(config_path=str(config_path))

    assert settings.database.host == "json-db"
    assert settings.database.port == 5432
    assert settings.jobs.polling_interval == 1.0
    assert settings.device.jit_compile is False
    assert settings.device.jit_backend == "inductor"


# -----------------------------------------------------------------------------
def test_technical_env_overrides_are_not_applied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    _write_json(config_path, _default_json_config())

    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        [
            "DATABASE_USER=legacy-user",
            "DATABASE_NAME=legacy-name",
        ],
    )
    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))

    settings = startup.reload_settings_for_tests(config_path=str(config_path))

    assert settings.database.username == "json_user"
    assert settings.database.database_name == "json_name"


# -----------------------------------------------------------------------------
def test_manager_get_block_and_get_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    _write_json(config_path, _default_json_config())

    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=127.0.0.1"])
    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))

    startup.reload_settings_for_tests(config_path=str(config_path))
    manager = startup.get_configuration_manager()

    database_block = manager.get_block("database")
    assert database_block["host"] == "json-db"
    assert manager.get_value("jobs", "polling_interval") == 1.0
    assert manager.get_value("device", "missing", default="fallback") == "fallback"


# -----------------------------------------------------------------------------
def test_reload_updates_cached_manager_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    payload = _default_json_config()
    _write_json(config_path, payload)

    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=127.0.0.1"])
    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))

    first = startup.reload_settings_for_tests(config_path=str(config_path))
    assert first.jobs.polling_interval == 1.0

    payload["jobs"] = {"polling_interval": 2.25}
    _write_json(config_path, payload)

    second = startup.reload_settings_for_tests(config_path=str(config_path))
    assert second.jobs.polling_interval == 2.25


# -----------------------------------------------------------------------------
def test_missing_configuration_file_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=127.0.0.1"])
    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))

    with pytest.raises(RuntimeError, match="Configuration file not found"):
        _ = startup.reload_settings_for_tests(config_path=str(tmp_path / "missing.json"))


# -----------------------------------------------------------------------------
def test_invalid_configuration_file_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    config_path.write_text("{not-json", encoding="utf-8")

    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=127.0.0.1"])
    monkeypatch.setattr(environment, "ENV_FILE_PATH", str(env_path))

    with pytest.raises(RuntimeError, match="Unable to load configuration"):
        _ = startup.reload_settings_for_tests(config_path=str(config_path))
