"""Runtime capability checks for optional backend execution features."""

from __future__ import annotations

import sys

###############################################################################
JIT_UNSUPPORTED_PYTHON_MESSAGE = (
    "JIT compilation is not supported by torch.compile on Python 3.14 or newer. "
    "Disable JIT or run FAIRS with Python 3.13 or earlier."
)
JIT_UNAVAILABLE_MESSAGE = (
    "JIT compilation requires a PyTorch runtime that exposes torch.compile."
)

###############################################################################
def get_jit_runtime_error(jit_compile: bool) -> str | None:
    """Return an actionable error when the selected runtime cannot compile models."""
    if not jit_compile:
        return None

    # The bundled PyTorch build raises this limitation from torch.compile on
    # Python 3.14, so reject it before a worker is started or a setting is saved.
    if sys.version_info >= (3, 14):
        return JIT_UNSUPPORTED_PYTHON_MESSAGE

    try:
        import torch
    except Exception:  # noqa: BLE001
        return JIT_UNAVAILABLE_MESSAGE
    if not callable(getattr(torch, "compile", None)):
        return JIT_UNAVAILABLE_MESSAGE
    return None

###############################################################################
def validate_jit_runtime(jit_compile: bool) -> None:
    """Raise a user-facing validation error for an unavailable JIT runtime."""
    error = get_jit_runtime_error(jit_compile)
    if error is not None:
        raise ValueError(error)
