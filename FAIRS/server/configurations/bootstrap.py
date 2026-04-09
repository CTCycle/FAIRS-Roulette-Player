from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv

from FAIRS.server.common.constants import ENV_FILE_PATH
from FAIRS.server.common.utils.logger import logger


@dataclass
class EnvironmentBootstrapState:
    lock: Lock = field(default_factory=Lock)
    bootstrapped: bool = False


# -----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _bootstrap_state() -> EnvironmentBootstrapState:
    return EnvironmentBootstrapState()


###############################################################################
def ensure_environment_loaded(*, force: bool = False) -> Path | None:
    state = _bootstrap_state()

    with state.lock:
        env_path = Path(ENV_FILE_PATH)
        if state.bootstrapped and not force:
            return env_path if env_path.exists() else None

        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
        else:
            logger.warning(".env file not found at: %s", env_path)

        state.bootstrapped = True
        return env_path if env_path.exists() else None


###############################################################################
def reset_environment_bootstrap_for_tests() -> None:
    state = _bootstrap_state()
    with state.lock:
        state.bootstrapped = False
