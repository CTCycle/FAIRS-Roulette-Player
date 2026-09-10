from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import uuid

from pydantic import ValidationError

from server.bootstrap import bootstrap_runtime
from server.common import path as shared_paths
from server.contracts.training import (
    CHECKPOINT_SCHEMA_VERSION,
    CheckpointConfiguration,
    TrainingSettings,
)

LEGACY_RUNTIME_ONLY_FIELDS = frozenset({"jit_compile", "jit_backend"})

###############################################################################
@dataclass(frozen=True)
class CheckpointMigration:
    checkpoint: str
    config_path: Path
    complete_path: Path
    payload: dict[str, object]
    needs_config_write: bool
    needs_complete_marker: bool

###############################################################################
def _read_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read checkpoint configuration: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Checkpoint configuration must be a JSON object: {path}")
    return value

###############################################################################
def _write_json_atomically(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.migration-{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()

###############################################################################
def _required_checkpoint_files(checkpoint_path: Path) -> tuple[Path, Path, Path]:
    return (
        shared_paths.checkpoint_saved_model_file(checkpoint_path),
        shared_paths.checkpoint_configuration_file(checkpoint_path),
        shared_paths.checkpoint_session_history_file(checkpoint_path),
    )

###############################################################################
def _plan_checkpoint(checkpoint_path: Path) -> CheckpointMigration:
    required_files = _required_checkpoint_files(checkpoint_path)
    missing_files = [str(path) for path in required_files if not path.is_file()]
    if missing_files:
        raise ValueError(
            f"Checkpoint '{checkpoint_path.name}' is incomplete; missing: "
            + ", ".join(missing_files)
        )

    config_path = shared_paths.checkpoint_configuration_file(checkpoint_path)
    complete_path = checkpoint_path / shared_paths.CHECKPOINT_COMPLETE_FILE_NAME
    raw = _read_json_object(config_path)
    schema_version = raw.get("schema_version")

    if schema_version == CHECKPOINT_SCHEMA_VERSION:
        candidate = dict(raw)
        needs_config_write = False
    elif schema_version is None:
        canonical_fields = set(TrainingSettings.model_fields)
        expected_legacy_fields = canonical_fields | set(LEGACY_RUNTIME_ONLY_FIELDS)
        actual_fields = set(raw)
        if actual_fields != expected_legacy_fields:
            missing = sorted(expected_legacy_fields - actual_fields)
            extra = sorted(actual_fields - expected_legacy_fields)
            details: list[str] = []
            if missing:
                details.append(f"missing {', '.join(missing)}")
            if extra:
                details.append(f"unexpected {', '.join(extra)}")
            raise ValueError(
                f"Checkpoint '{checkpoint_path.name}' has an unknown unversioned "
                f"configuration shape ({'; '.join(details)})."
            )
        candidate = {
            key: value
            for key, value in raw.items()
            if key not in LEGACY_RUNTIME_ONLY_FIELDS
        }
        candidate["schema_version"] = CHECKPOINT_SCHEMA_VERSION
        needs_config_write = True
    else:
        raise ValueError(
            f"Checkpoint '{checkpoint_path.name}' has unsupported schema_version "
            f"{schema_version!r}."
        )

    try:
        validated = CheckpointConfiguration.model_validate(candidate)
    except ValidationError as exc:
        raise ValueError(
            f"Checkpoint '{checkpoint_path.name}' cannot be migrated safely."
        ) from exc

    return CheckpointMigration(
        checkpoint=checkpoint_path.name,
        config_path=config_path,
        complete_path=complete_path,
        payload=validated.model_dump(),
        needs_config_write=needs_config_write,
        needs_complete_marker=not complete_path.is_file(),
    )

###############################################################################
def plan_migrations() -> list[CheckpointMigration]:
    root = shared_paths.CHECKPOINT_PATH
    if not root.exists():
        return []

    migrations: list[CheckpointMigration] = []
    errors: list[str] = []
    for checkpoint_path in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        if not checkpoint_path.is_dir() or checkpoint_path.name.startswith("."):
            continue
        try:
            migrations.append(_plan_checkpoint(checkpoint_path))
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        raise ValueError(
            "Checkpoint migration preflight failed; no files were changed:\n- "
            + "\n- ".join(errors)
        )
    return migrations

###############################################################################
def apply_migrations(migrations: list[CheckpointMigration]) -> None:
    for migration in migrations:
        if migration.needs_config_write:
            _write_json_atomically(migration.config_path, migration.payload)
        if migration.needs_complete_marker:
            migration.complete_path.write_text("complete\n", encoding="utf-8")

###############################################################################
def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight and optionally migrate FAIRS checkpoints to the current "
            "strict checkpoint schema."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="apply the preflighted migration; the default is read-only",
    )
    options = parser.parse_args(arguments)

    bootstrap_runtime()
    try:
        migrations = plan_migrations()
    except ValueError as exc:
        print(str(exc))
        return 1

    pending = [
        migration
        for migration in migrations
        if migration.needs_config_write or migration.needs_complete_marker
    ]
    if not pending:
        print("All checkpoints already use the current schema.")
        return 0

    for migration in pending:
        actions: list[str] = []
        if migration.needs_config_write:
            actions.append(f"write schema_version={CHECKPOINT_SCHEMA_VERSION}")
        if migration.needs_complete_marker:
            actions.append("write completion marker")
        print(f"{migration.checkpoint}: {', '.join(actions)}")

    if not options.apply:
        print("Preflight only. Re-run with --apply to write the migration.")
        return 0

    apply_migrations(migrations)
    print(f"Migrated {len(pending)} checkpoint(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
