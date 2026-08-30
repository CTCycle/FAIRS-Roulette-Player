from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

import pytest

from server.configurations import environment, startup

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


###############################################################################
@pytest.fixture(autouse=True)
def reset_configuration_state(monkeypatch: pytest.MonkeyPatch) -> None:
    startup.get_configuration_manager.cache_clear()
    environment.reset_environment_for_tests()
    for env_name in DATABASE_ENV_KEYS:
        monkeypatch.delenv(env_name, raising=False)
    yield
    startup.get_configuration_manager.cache_clear()
    environment.reset_environment_for_tests()


###############################################################################
def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


###############################################################################
def _write_env(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


###############################################################################
def _default_json_config() -> dict[str, object]:
    return {
        "jobs": {"polling_interval": 1.0},
        "device": {
            "jit_compile": False,
            "jit_backend": "inductor",
            "use_mixed_precision": False,
        },
    }


###############################################################################
def test_environment_overrides_existing_process_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=from_dotenv"])

    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)
    monkeypatch.setenv("FASTAPI_HOST", "from_process")

    environment.load_environment()

    assert os.getenv("FASTAPI_HOST") == "from_dotenv"


###############################################################################
def test_environment_creates_missing_env_from_example(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    example_path = tmp_path / ".env.example"
    example_contents = "FASTAPI_HOST=from-example\nEMBEDDED_DATABASE=true\n"
    example_path.write_text(example_contents, encoding="utf-8")

    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)
    monkeypatch.setattr(
        environment.shared_paths,
        "ENV_EXAMPLE_FILE_PATH",
        example_path,
    )

    loaded_path = environment.load_environment(force=True)

    assert loaded_path == env_path
    assert env_path.read_text(encoding="utf-8") == example_contents
    assert os.getenv("FASTAPI_HOST") == "from-example"


###############################################################################
def test_environment_preserves_existing_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    example_path = tmp_path / ".env.example"
    existing_contents = "FASTAPI_HOST=from-existing\n"
    env_path.write_text(existing_contents, encoding="utf-8")
    example_path.write_text("FASTAPI_HOST=from-example\n", encoding="utf-8")

    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)
    monkeypatch.setattr(
        environment.shared_paths,
        "ENV_EXAMPLE_FILE_PATH",
        example_path,
    )

    environment.load_environment(force=True)

    assert env_path.read_text(encoding="utf-8") == existing_contents
    assert os.getenv("FASTAPI_HOST") == "from-existing"


###############################################################################
def test_environment_requires_template_when_env_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)
    monkeypatch.setattr(
        environment.shared_paths,
        "ENV_EXAMPLE_FILE_PATH",
        tmp_path / ".env.example",
    )

    with pytest.raises(RuntimeError, match="template was not found"):
        environment.load_environment(force=True)


###############################################################################
def test_environment_load_is_idempotent_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=first"])

    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)

    environment.load_environment()
    _write_env(env_path, ["FASTAPI_HOST=second"])
    environment.load_environment()

    assert os.getenv("FASTAPI_HOST") == "first"


###############################################################################
def test_environment_force_reload_applies_updated_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=first"])
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)

    environment.load_environment()
    _write_env(env_path, ["FASTAPI_HOST=second"])
    environment.load_environment(force=True)

    assert os.getenv("FASTAPI_HOST") == "second"


###############################################################################
def test_server_package_import_does_not_load_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["KERAS_BACKEND=torch"])

    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)
    monkeypatch.setenv("KERAS_BACKEND", "tensorflow")

    import server

    importlib.reload(server)
    assert server is not None
    assert os.getenv("KERAS_BACKEND") == "tensorflow"


###############################################################################
def test_server_settings_use_json_configuration_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    _write_json(config_path, _default_json_config())

    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        [
            "FASTAPI_HOST=127.0.0.1",
            "EMBEDDED_DATABASE=false",
            "DATABASE_HOST=env-db",
            "DATABASE_PORT=5432",
            "DATABASE_NAME=env_name",
            "DATABASE_USERNAME=env_user",
            "DATABASE_PASSWORD=env_pass",
        ],
    )
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)

    settings = startup.reload_settings_for_tests(config_path=str(config_path))

    assert settings.database.host == "env-db"
    assert settings.database.port == 5432
    assert settings.database.database_name == "env_name"
    assert settings.database.username == "env_user"
    assert settings.jobs.polling_interval == 1.0
    assert settings.device.jit_compile is False
    assert settings.device.jit_backend == "inductor"


###############################################################################
def test_database_settings_are_loaded_from_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    _write_json(config_path, _default_json_config())

    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        [
            "EMBEDDED_DATABASE=false",
            "DATABASE_ENGINE=postgresql+psycopg",
            "DATABASE_HOST=env-host",
            "DATABASE_PORT=5544",
            "DATABASE_USERNAME=env-user",
            "DATABASE_NAME=env-name",
        ],
    )
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)

    settings = startup.reload_settings_for_tests(config_path=str(config_path))

    assert settings.database.host == "env-host"
    assert settings.database.port == 5544
    assert settings.database.username == "env-user"
    assert settings.database.database_name == "env-name"


###############################################################################
def test_manager_get_block_and_get_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    _write_json(config_path, _default_json_config())

    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        [
            "FASTAPI_HOST=127.0.0.1",
            "EMBEDDED_DATABASE=false",
            "DATABASE_HOST=env-db",
            "DATABASE_PORT=5432",
            "DATABASE_NAME=env_name",
            "DATABASE_USERNAME=env_user",
            "DATABASE_PASSWORD=env_pass",
        ],
    )
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)

    startup.reload_settings_for_tests(config_path=str(config_path))
    manager = startup.get_configuration_manager()

    database_block = manager.get_block("database")
    assert database_block["host"] == "env-db"
    assert "database_url" not in database_block
    assert manager.get_value("jobs", "polling_interval") == 1.0
    assert manager.get_value("device", "missing", default="fallback") == "fallback"


###############################################################################
def test_reload_updates_cached_manager_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    payload = _default_json_config()
    _write_json(config_path, payload)

    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        [
            "FASTAPI_HOST=127.0.0.1",
            "EMBEDDED_DATABASE=true",
        ],
    )
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)

    first = startup.reload_settings_for_tests(config_path=str(config_path))
    assert first.jobs.polling_interval == 1.0

    payload["jobs"] = {"polling_interval": 2.25}
    _write_json(config_path, payload)

    second = startup.reload_settings_for_tests(config_path=str(config_path))
    assert second.jobs.polling_interval == 2.25


###############################################################################
def test_missing_configuration_file_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=127.0.0.1", "EMBEDDED_DATABASE=true"])
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)

    with pytest.raises(RuntimeError, match="Configuration file not found"):
        _ = startup.reload_settings_for_tests(
            config_path=str(tmp_path / "missing.json")
        )


###############################################################################
def test_invalid_configuration_file_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    config_path.write_text("{not-json", encoding="utf-8")

    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=127.0.0.1", "EMBEDDED_DATABASE=true"])
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)

    with pytest.raises(RuntimeError, match="Unable to load configuration"):
        _ = startup.reload_settings_for_tests(config_path=str(config_path))
