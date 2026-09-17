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
JIT_INDUCTOR_WINDOWS_MESSAGE = (
    "The JIT backend 'inductor' requires Triton, which is unavailable in the "
    "supported Windows runtime. Select the 'eager' backend or use a platform "
    "with Triton support."
)

###############################################################################
def get_jit_runtime_error(
    jit_compile: bool,
    jit_backend: str = "eager",
) -> str | None:
    """Return an actionable error when the selected runtime cannot compile models."""
    if not jit_compile:
        return None

    # The supported launcher runtime is Python 3.13. Keep this guard for
    # manually selected or future runtimes that are known to be incompatible.
    if sys.version_info >= (3, 14):
        return JIT_UNSUPPORTED_PYTHON_MESSAGE

    try:
        import torch
    except Exception:  # noqa: BLE001
        return JIT_UNAVAILABLE_MESSAGE
    if not callable(getattr(torch, "compile", None)):
        return JIT_UNAVAILABLE_MESSAGE
    if sys.platform == "win32" and jit_backend.strip().lower() == "inductor":
        return JIT_INDUCTOR_WINDOWS_MESSAGE
    return None

###############################################################################
def validate_jit_runtime(jit_compile: bool, jit_backend: str = "eager") -> None:
    """Raise a user-facing validation error for an unavailable JIT runtime."""
    error = get_jit_runtime_error(jit_compile, jit_backend)
    if error is not None:
        raise ValueError(error)
