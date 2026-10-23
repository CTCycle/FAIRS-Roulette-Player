# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import base64
import json
import os
import pytest
import server.configurations.database_config as database_config
import importlib
from pathlib import Path
from server.common import path as shared_paths
from server.configurations.database_config import DatabaseConfigurationError, DatabaseConfigurationStore
from server.contracts.database_configuration import DatabaseConfigurationInput
from server.configurations import environment

# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

###############################################################################
def _protector(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")

###############################################################################
def _unprotector(value: str) -> str:
    return base64.b64decode(value).decode("utf-8")

###############################################################################
def _store(
    tmp_path: Path,
    *,
    protector=_protector,
    unprotector=_unprotector,
) -> DatabaseConfigurationStore:
    return DatabaseConfigurationStore(
        tmp_path / "database-config.json",
        environment_file=tmp_path / ".env",
        password_protector=protector,
        password_unprotector=unprotector,
    )

###############################################################################
def test_default_config_is_database_only_and_atomic(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("APP_NAME=FAIRS\n", encoding="utf-8")
    monkeypatch.setattr(shared_paths, "DATABASE_PATH", tmp_path / "database.db")
    store = _store(tmp_path)

    loaded = store.load_or_initialize()
    document = json.loads(store.path.read_text(encoding="utf-8"))

    assert loaded.settings.embedded_database is True
    assert loaded.sqlite_path == (tmp_path / "database.db").resolve()
    assert set(document) == {"schema_version", "backend", "sqlite"}
    assert document["backend"] == "sqlite"
    assert document["sqlite"]["path"] == str((tmp_path / "database.db").resolve())
    assert env_path.read_text(encoding="utf-8") == "APP_NAME=FAIRS\n"

###############################################################################
def test_database_environment_values_are_ignored_and_scrubbed(
    tmp_path: Path, monkeypatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# Keep this comment\nFASTAPI_HOST=127.0.0.1\n"
        "EMBEDDED_DATABASE=false\nDATABASE_ENGINE=postgresql+psycopg\n"
        "DATABASE_HOST=db.example\nDATABASE_PORT=5544\nDATABASE_NAME=fairs\n"
        "DATABASE_USERNAME=service\nDATABASE_PASSWORD=legacy-secret\n"
        "DATABASE_SSL=true\nDATABASE_CONNECT_TIMEOUT=25\n"
        "DATABASE_INSERT_BATCH_SIZE=250\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(shared_paths, "DATABASE_PATH", tmp_path / "database.db")
    store = _store(tmp_path)

    loaded = store.load_or_initialize()
    persisted = store.path.read_text(encoding="utf-8")
    public = store.to_public(loaded).model_dump(mode="json")

    assert loaded.document.backend == "sqlite"
    assert loaded.settings.embedded_database is True
    assert loaded.sqlite_path == (tmp_path / "database.db").resolve()
    assert "legacy-secret" not in persisted
    assert "password_configured" not in persisted
    assert public["password_configured"] is False
    assert "legacy-secret" not in json.dumps(public)
    cleaned = env_path.read_text(encoding="utf-8")
    assert "FASTAPI_HOST=127.0.0.1" in cleaned
    assert "Keep this comment" in cleaned
    assert "DATABASE_" not in cleaned
    assert "EMBEDDED_DATABASE" not in cleaned

###############################################################################
def test_blank_password_retains_saved_secret_and_explicit_clear_removes_it(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    original = DatabaseConfigurationInput(
        backend="postgresql",
        host="db.example",
        database_name="fairs",
        username="service",
        password="top-secret",
    )
    store.write(original, password=original.password)

    retain = DatabaseConfigurationInput(
        backend="postgresql",
        host="db.example",
        database_name="fairs",
        username="service",
        password="",
    )
    normalized, password = store.resolve_input(retain)
    store.write(normalized, password=password)
    assert store.current().settings.password == "top-secret"

    clear = retain.model_copy(update={"clear_password": True})
    normalized, password = store.resolve_input(clear)
    store.write(normalized, password=password)
    assert store.current().settings.password is None
    assert store.to_public(store.current()).password_configured is False

###############################################################################
def test_invalid_and_corrupt_files_fail_closed_without_default_fallback(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    original = '{"schema_version": 99, "backend": "sqlite", "sqlite": {"path": "x", "insert_batch_size": 1}}'
    store.path.write_text(original, encoding="utf-8")

    with pytest.raises(DatabaseConfigurationError, match="invalid"):
        store.current()
    assert store.path.read_text(encoding="utf-8") == original

    store.path.write_text("{broken", encoding="utf-8")
    with pytest.raises(DatabaseConfigurationError, match="invalid"):
        store.load_or_initialize()
    assert store.path.read_text(encoding="utf-8") == "{broken"

###############################################################################
def test_unknown_database_config_keys_are_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "backend": "sqlite",
                "sqlite": {"path": "db.sqlite", "insert_batch_size": 1},
                "jobs": {"polling_interval": 1.0},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DatabaseConfigurationError):
        store.current()

###############################################################################
def test_blank_sqlite_path_in_config_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "backend": "sqlite",
                "sqlite": {"path": "   ", "insert_batch_size": 1000},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DatabaseConfigurationError, match="invalid"):
        store.current()

###############################################################################
def test_atomic_replace_failure_preserves_previous_database_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    first = DatabaseConfigurationInput(backend="sqlite", sqlite_path=str(tmp_path / "first.db"))
    store.write(first)
    before = store.path.read_bytes()
    monkeypatch.setattr(
        database_config.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace failed")),
    )

    with pytest.raises(DatabaseConfigurationError, match="write"):
        store.write(
            DatabaseConfigurationInput(
                backend="sqlite", sqlite_path=str(tmp_path / "second.db")
            )
        )

    assert store.path.read_bytes() == before
    assert list(tmp_path.glob(".database-config.json.*.tmp")) == []

###############################################################################
def test_invalid_old_database_environment_values_do_not_block_default(
    tmp_path: Path, monkeypatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("EMBEDDED_DATABASE=false\nDATABASE_HOST=missing-parts\n", encoding="utf-8")
    monkeypatch.setattr(shared_paths, "DATABASE_PATH", tmp_path / "database.db")
    store = _store(tmp_path)

    loaded = store.load_or_initialize()

    assert loaded.document.backend == "sqlite"
    assert loaded.sqlite_path == (tmp_path / "database.db").resolve()
    assert store.path.is_file()
    assert "DATABASE_HOST" not in env_path.read_text(encoding="utf-8")

###############################################################################
@pytest.mark.skipif(os.name != "nt", reason="DPAPI is available on Windows only")
def test_windows_dpapi_protects_and_recovers_password() -> None:
    secret = "fairs-dpapi-test-value"
    encrypted = database_config.protect_password(secret)
    assert encrypted != secret
    assert database_config.unprotect_password(encrypted) == secret

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
def test_environment_loads_network_runtime_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        [
            "API_BASE_URL=https://api.example.test",
            "CORS_ORIGINS=https://console.example.test,https://admin.example.test",
        ],
    )
    monkeypatch.setattr(environment.shared_paths, "ENV_FILE_PATH", env_path)

    environment.load_environment(force=True)

    assert os.getenv("API_BASE_URL") == "https://api.example.test"
    assert os.getenv("CORS_ORIGINS") == (
        "https://console.example.test,https://admin.example.test"
    )

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
