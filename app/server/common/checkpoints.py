from __future__ import annotations

from pathlib import Path

from server.common import path as shared_paths

MAX_CHECKPOINT_NAME_LENGTH = 128
CHECKPOINT_EMPTY_MESSAGE_TEXT = "Checkpoint name cannot be empty."

###############################################################################
def normalize_checkpoint_identifier(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError(CHECKPOINT_EMPTY_MESSAGE_TEXT)
    if len(candidate) > MAX_CHECKPOINT_NAME_LENGTH:
        raise ValueError("Checkpoint name is too long.")
    if candidate in {".", ".."}:
        raise ValueError("Invalid checkpoint name.")
    if any(ord(char) < 32 for char in candidate):
        raise ValueError("Checkpoint name contains invalid control characters.")
    if any(separator in candidate for separator in ("/", "\\", ":")):
        raise ValueError("Invalid checkpoint name.")
    if Path(candidate).name != candidate:
        raise ValueError("Invalid checkpoint name.")
    return candidate

###############################################################################
def resolve_checkpoint_path(checkpoint_name: str) -> Path:
    checkpoints_root = shared_paths.CHECKPOINT_PATH.resolve()
    checkpoint_path = (checkpoints_root / checkpoint_name).resolve()
    if checkpoints_root not in checkpoint_path.parents:
        raise ValueError("Invalid checkpoint path.")
    return checkpoint_path
