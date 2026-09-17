from __future__ import annotations

import sys

import pytest

from server.common import runtime_capabilities

###############################################################################
def test_disabled_jit_has_no_runtime_requirement() -> None:
    assert runtime_capabilities.get_jit_runtime_error(False) is None

###############################################################################
def test_unsupported_python_rejects_jit_before_model_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_capabilities.sys, "version_info", (3, 14, 0))
    with pytest.raises(ValueError, match="Python 3.14"):
        runtime_capabilities.validate_jit_runtime(True, "eager")

###############################################################################
@pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason="The supported runtime contract excludes Python 3.14 and newer.",
)
def test_supported_runtime_accepts_jit() -> None:
    assert runtime_capabilities.validate_jit_runtime(True, "eager") is None

###############################################################################
def test_windows_inductor_is_rejected_before_torch_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_capabilities.sys, "version_info", (3, 13, 15))
    monkeypatch.setattr(runtime_capabilities.sys, "platform", "win32")

    with pytest.raises(ValueError, match="Triton"):
        runtime_capabilities.validate_jit_runtime(True, "inductor")
