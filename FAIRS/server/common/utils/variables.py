from __future__ import annotations

import os
import warnings
from typing import Any

from FAIRS.server.configurations.bootstrap import ensure_environment_loaded


class EnvironmentVariables:
    def __init__(self) -> None:
        warnings.warn(
            "EnvironmentVariables is deprecated. Use FAIRS.server.configurations settings APIs.",
            DeprecationWarning,
            stacklevel=2,
        )
        ensure_environment_loaded()

    # -------------------------------------------------------------------------
    def get(self, key: str, default: str | None = None) -> str | None:
        return os.getenv(key, default)


class _EnvironmentVariablesProxy:
    def __init__(self) -> None:
        self._instance: EnvironmentVariables | None = None

    # -------------------------------------------------------------------------
    def _resolve(self) -> EnvironmentVariables:
        if self._instance is None:
            self._instance = EnvironmentVariables()
        return self._instance

    # -------------------------------------------------------------------------
    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)


env_variables = _EnvironmentVariablesProxy()
