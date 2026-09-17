from __future__ import annotations

import sys

import pytest

from server.common import runtime_capabilities

###############################################################################
def test_disabled_jit_has_no_runtime_requirement() -> None:
    assert runtime_capabilities.get_jit_runtime_error(False) is None

###############################################################################
@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="The bundled Python 3.14 runtime is required to exercise this guard.",
)
def test_bundled_python_rejects_jit_before_model_construction() -> None:
    with pytest.raises(ValueError, match="Python 3.14"):
        runtime_capabilities.validate_jit_runtime(True)
