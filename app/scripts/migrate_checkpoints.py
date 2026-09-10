from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from server.common import path as shared_paths
from server.contracts.training import (
    CHECKPOINT_FORMAT_VERSION,
    CheckpointConfiguration,
    TrainingConfig,
)

KNOWN_LEGACY_ONLY_FIELDS = {"jit_compile", "jit_backend"}


###############################################################################
def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read checkpoint configuration: {path}") from exc


###############################################################################
def _render_current_configuration(raw: Any, path: Path) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        raise ValueError(f"Checkpoint configuration must be an object: {path}")

    if "format_version" in raw or "training" in raw:
        try:
            CheckpointConfiguration.model_validate(raw)
        except ValidationError as exc:
            raise ValueError(
                f"Unsupported or invalid versioned checkpoint configuration: {path}"
            ) from exc
        return None

    expected_fields = set(TrainingConfig.model_fields)
    provided_fields = set(raw)
    missing = expected_fields - provided_fields
    unexpected = provided_fields - expected_fields - KNOWN_LEGACY_ONLY_FIELDS
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing={','.join(sorted(missing))}")
        if unexpected:
            details.append(f"unexpected={','.join(sorted(unexpected))}")
        raise ValueError(
            f"Legacy checkpoint shape is not the known migratable format: {path} "
            f"({' '.join(details)})"
        )

    training_payload = {key: raw[key] for key in expected_fields}
    try:
        training = TrainingConfig.model_validate(training_payload)
        current = CheckpointConfiguration(
            format_version=CHECKPOINT_FORMAT_VERSION,
            training=training,
        )
    except ValidationError as exc:
        raise ValueError(f"Legacy checkpoint values are invalid: {path}") from exc
    return current.model_dump()


###############################################################################
def _write_json_atomically(path: Path, payload: dict[str, Any]) -> None:
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(json.dumps(payload), encoding="utf-8")
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


###############################################################################
def _configuration_paths(root: Path) -> list[Path]:
    if not root.exists():
        return []
    paths: list[Path] = []
    for checkpoint in sorted(root.iterdir(), key=lambda item: item.name):
        if checkpoint.name.startswith(".") or not checkpoint.is_dir():
            continue
        config_path = shared_paths.checkpoint_configuration_file(checkpoint)
        if config_path.is_file():
            paths.append(config_path)
    return paths


###############################################################################
def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight or apply the one-time migration from the known unversioned "
            "checkpoint configuration to the current versioned format."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write validated migrations; without this flag the command is read-only",
    )
    options = parser.parse_args(arguments)

    migrations: list[tuple[Path, dict[str, Any]]] = []
    for config_path in _configuration_paths(shared_paths.CHECKPOINT_PATH):
        raw = _load_json(config_path)
        migrated = _render_current_configuration(raw, config_path)
        if migrated is not None:
            migrations.append((config_path, migrated))

    if not migrations:
        print("All checkpoint configurations already use the current format.")
        return 0

    for config_path, _ in migrations:
        print(f"Migrate: {config_path}")

    if not options.apply:
        print(f"Preflight complete: {len(migrations)} checkpoint(s) require migration.")
        print("Re-run with --apply to perform the validated one-time conversion.")
        return 0

    for config_path, payload in migrations:
        _write_json_atomically(config_path, payload)
    print(f"Migrated {len(migrations)} checkpoint configuration(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
