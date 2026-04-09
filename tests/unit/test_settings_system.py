from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

import pytest

from FAIRS.server.configurations import bootstrap
from FAIRS.server.configurations.settings import (
    AppSettings,
    get_app_settings,
    get_server_settings,
    reload_settings_for_tests,
)


###############################################################################
@pytest.fixture(autouse=True)
def reset_configuration_state() -> None:
    get_app_settings.cache_clear()
    bootstrap.reset_environment_bootstrap_for_tests()
    yield
    get_app_settings.cache_clear()
    bootstrap.reset_environment_bootstrap_for_tests()


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
def test_bootstrap_environment_overrides_existing_process_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=from_dotenv"])

    monkeypatch.setattr(bootstrap, "ENV_FILE_PATH", str(env_path))
    monkeypatch.setenv("FASTAPI_HOST", "from_process")

    bootstrap.ensure_environment_loaded()

    assert os.getenv("FASTAPI_HOST") == "from_dotenv"


# -----------------------------------------------------------------------------
def test_bootstrap_is_idempotent_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=first"])

    monkeypatch.setattr(bootstrap, "ENV_FILE_PATH", str(env_path))

    bootstrap.ensure_environment_loaded()
    _write_env(env_path, ["FASTAPI_HOST=second"])
    bootstrap.ensure_environment_loaded()

    assert os.getenv("FASTAPI_HOST") == "first"


# -----------------------------------------------------------------------------
def test_bootstrap_force_reload_applies_updated_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=first"])
    monkeypatch.setattr(bootstrap, "ENV_FILE_PATH", str(env_path))

    bootstrap.ensure_environment_loaded()
    _write_env(env_path, ["FASTAPI_HOST=second"])
    bootstrap.ensure_environment_loaded(force=True)

    assert os.getenv("FASTAPI_HOST") == "second"


# -----------------------------------------------------------------------------
def test_server_package_import_bootstraps_env_early(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["KERAS_BACKEND=torch"])

    monkeypatch.setattr(bootstrap, "ENV_FILE_PATH", str(env_path))
    monkeypatch.setenv("KERAS_BACKEND", "tensorflow")

    import FAIRS.server as server_package

    importlib.reload(server_package)

    assert os.getenv("KERAS_BACKEND") == "torch"


# -----------------------------------------------------------------------------
def test_technical_env_overrides_json_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    _write_json(config_path, _default_json_config())

    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        [
            "DATABASE_HOST=env-db",
            "DATABASE_PORT=6543",
            "JOBS_POLLING_INTERVAL=2.5",
            "DEVICE_JIT_COMPILE=true",
            "DEVICE_JIT_BACKEND=cudagraphs",
        ],
    )
    monkeypatch.setattr(bootstrap, "ENV_FILE_PATH", str(env_path))

    settings = get_server_settings(config_path=str(config_path))

    assert settings.database.host == "env-db"
    assert settings.database.port == 6543
    assert settings.jobs.polling_interval == 2.5
    assert settings.device.jit_compile is True
    assert settings.device.jit_backend == "cudagraphs"


# -----------------------------------------------------------------------------
def test_only_explicit_technical_env_keys_are_applied(
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
    monkeypatch.setattr(bootstrap, "ENV_FILE_PATH", str(env_path))

    settings = get_server_settings(config_path=str(config_path))

    assert settings.database.username == "json_user"
    assert settings.database.database_name == "json_name"


# -----------------------------------------------------------------------------
def test_runtime_env_fields_are_typed_in_app_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    _write_json(config_path, _default_json_config())

    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        [
            "FASTAPI_HOST=0.0.0.0",
            "FASTAPI_PORT=5111",
            "UI_HOST=127.0.0.1",
            "UI_PORT=8111",
            "ENABLE_API_DOCS=false",
            "FAIRS_ALLOW_DIRECT_API_ROUTES=false",
            "RELOAD=true",
            "MPLBACKEND=Agg",
            "KERAS_BACKEND=torch",
        ],
    )

    monkeypatch.setattr(bootstrap, "ENV_FILE_PATH", str(env_path))
    monkeypatch.setattr(AppSettings, "_configuration_file", str(config_path))
    app_settings = reload_settings_for_tests()

    assert app_settings.fastapi_host == "0.0.0.0"
    assert app_settings.fastapi_port == 5111
    assert app_settings.ui_port == 8111
    assert app_settings.enable_api_docs is False
    assert app_settings.fairs_allow_direct_api_routes is False
    assert app_settings.reload is True
    assert app_settings.mplbackend == "Agg"
    assert app_settings.keras_backend == "torch"


# -----------------------------------------------------------------------------
def test_missing_configuration_file_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=127.0.0.1"])
    monkeypatch.setattr(bootstrap, "ENV_FILE_PATH", str(env_path))

    with pytest.raises(RuntimeError, match="Configuration file not found"):
        _ = get_server_settings(config_path=str(tmp_path / "missing.json"))


# -----------------------------------------------------------------------------
def test_invalid_configuration_file_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "configurations.json"
    config_path.write_text("{not-json", encoding="utf-8")

    env_path = tmp_path / ".env"
    _write_env(env_path, ["FASTAPI_HOST=127.0.0.1"])
    monkeypatch.setattr(bootstrap, "ENV_FILE_PATH", str(env_path))

    with pytest.raises(RuntimeError, match="Unable to load configuration"):
        _ = get_server_settings(config_path=str(config_path))
