from __future__ import annotations

import os

from server.common.constants import CHECKPOINT_PATH

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
    if os.path.basename(candidate) != candidate:
        raise ValueError("Invalid checkpoint name.")
    return candidate


###############################################################################
def resolve_checkpoint_path(checkpoint_name: str) -> str:
    checkpoints_root = os.path.realpath(CHECKPOINT_PATH)
    checkpoint_path = os.path.realpath(os.path.join(checkpoints_root, checkpoint_name))
    if os.path.commonpath([checkpoints_root, checkpoint_path]) != checkpoints_root:
        raise ValueError("Invalid checkpoint path.")
    return checkpoint_path
