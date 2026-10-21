# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

from server.configurations import environment


###############################################################################
@pytest.fixture(autouse=True)
def reset_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    environment.reset_environment_for_tests()
    monkeypatch.delenv("DATABASE_HOST", raising=False)
    monkeypatch.delenv("EMBEDDED_DATABASE", raising=False)
    yield
    environment.reset_environment_for_tests()


###############################################################################
def _write_env(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    monkeypatch.setattr(environment.shared_paths, "ENV_EXAMPLE_FILE_PATH", example_path)

    assert environment.load_environment(force=True) == env_path
    assert env_path.read_text(encoding="utf-8") == example_contents
    assert os.getenv("FASTAPI_HOST") == "from-example"
    assert "EMBEDDED_DATABASE" not in os.environ


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
    monkeypatch.setattr(environment.shared_paths, "ENV_EXAMPLE_FILE_PATH", example_path)

    environment.load_environment(force=True)

    assert env_path.read_text(encoding="utf-8") == existing_contents
    assert os.getenv("FASTAPI_HOST") == "from-existing"


###############################################################################
def test_environment_requires_template_when_env_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", tmp_path / ".env")
    monkeypatch.setattr(
        environment.shared_paths, "ENV_EXAMPLE_FILE_PATH", tmp_path / ".env.example"
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
def test_environment_does_not_load_database_connection_variables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        ["FASTAPI_HOST=local", "DATABASE_HOST=legacy-host", "DATABASE_PASSWORD=legacy-secret"],
    )
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)
    monkeypatch.setenv("DATABASE_HOST", "process-host")
    monkeypatch.setenv("DATABASE_PASSWORD", "process-secret")

    environment.load_environment(force=True)

    assert os.getenv("FASTAPI_HOST") == "local"
    assert "DATABASE_HOST" not in os.environ
    assert "DATABASE_PASSWORD" not in os.environ
    assert "DATABASE_PASSWORD=legacy-secret" in env_path.read_text(encoding="utf-8")


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
