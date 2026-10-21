# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import pytest

import server.configurations.database_config as database_config
from server.common import path as shared_paths
from server.configurations.database_config import (
    DatabaseConfigurationError,
    DatabaseConfigurationStore,
)
from server.contracts.database_configuration import DatabaseConfigurationInput


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

    loaded = store.load_or_migrate()
    document = json.loads(store.path.read_text(encoding="utf-8"))

    assert loaded.settings.embedded_database is True
    assert loaded.sqlite_path == (tmp_path / "database.db").resolve()
    assert set(document) == {"schema_version", "backend", "sqlite"}
    assert document["backend"] == "sqlite"
    assert document["sqlite"]["path"] == str((tmp_path / "database.db").resolve())
    assert env_path.read_text(encoding="utf-8") == "APP_NAME=FAIRS\n"


###############################################################################
def test_legacy_postgres_values_migrate_and_only_database_keys_are_removed(
    tmp_path: Path,
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
    store = _store(tmp_path)

    loaded = store.load_or_migrate()
    persisted = store.path.read_text(encoding="utf-8")
    public = store.to_public(loaded).model_dump(mode="json")

    assert loaded.document.backend == "postgresql"
    assert loaded.settings.engine == "postgresql+psycopg"
    assert loaded.settings.host == "db.example"
    assert loaded.settings.port == 5544
    assert loaded.settings.password == "legacy-secret"
    assert loaded.settings.ssl is True
    assert loaded.settings.connect_timeout == 25
    assert loaded.settings.insert_batch_size == 250
    assert "legacy-secret" not in persisted
    assert "password_configured" not in persisted
    assert public["password_configured"] is True
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
        store.load_or_migrate()
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
def test_invalid_legacy_postgres_config_does_not_create_a_default(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("EMBEDDED_DATABASE=false\nDATABASE_HOST=missing-parts\n", encoding="utf-8")
    store = _store(tmp_path)

    with pytest.raises(DatabaseConfigurationError, match="incomplete or invalid"):
        store.load_or_migrate()

    assert not store.path.exists()
    assert "DATABASE_HOST" in env_path.read_text(encoding="utf-8")


###############################################################################
@pytest.mark.skipif(os.name != "nt", reason="DPAPI is available on Windows only")
def test_windows_dpapi_protects_and_recovers_password() -> None:
    secret = "fairs-dpapi-test-value"
    encrypted = database_config.protect_password(secret)
    assert encrypted != secret
    assert database_config.unprotect_password(encrypted) == secret
