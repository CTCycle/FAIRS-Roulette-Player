from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import shutil
from threading import Lock

from dotenv import load_dotenv

from server.common import path as shared_paths
from server.common.utils.logger import logger

###############################################################################
@dataclass
class _EnvironmentState:
    lock: Lock = field(default_factory=Lock)
    loaded: bool = False

###############################################################################
@lru_cache(maxsize=1)
def _environment_state() -> _EnvironmentState:
    return _EnvironmentState()

###############################################################################
def ensure_environment_file() -> Path:
    env_path = shared_paths.ENV_FILE_PATH
    if env_path.is_file():
        return env_path

    example_path = shared_paths.ENV_EXAMPLE_FILE_PATH
    if not example_path.is_file():
        raise RuntimeError(
            f"Environment file is missing and its template was not found: {example_path}"
        )

    env_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with example_path.open("rb") as source, env_path.open("xb") as destination:
            shutil.copyfileobj(source, destination)
    except FileExistsError:
        pass

    logger.info("Created environment file from template: %s", env_path)
    return env_path

###############################################################################
def load_environment(*, force: bool = False) -> Path | None:
    state = _environment_state()
    env_path = shared_paths.ENV_FILE_PATH
    with state.lock:
        if state.loaded and not force:
            return env_path if env_path.exists() else None

        ensure_environment_file()
        load_dotenv(dotenv_path=env_path, override=True)

        state.loaded = True
        return env_path

###############################################################################
def reset_environment_for_tests() -> None:
    state = _environment_state()
    with state.lock:
        state.loaded = False
