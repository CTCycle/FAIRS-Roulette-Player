from __future__ import annotations


class CheckpointReferenceError(RuntimeError):
    """Raised when dataset deletion would invalidate checkpoint metadata."""


__all__ = ["CheckpointReferenceError"]
