from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
APP_DIR = ROOT_DIR / "app"
SERVER_DIR = APP_DIR / "server"
CLIENT_DIR = APP_DIR / "client"
SETTINGS_DIR = ROOT_DIR / "settings"
CACHE_PATH = ROOT_DIR / "runtimes" / "cache"
DATA_DIR: Path | None = None
RESOURCES_PATH = APP_DIR / "resources"
LOGS_PATH = RESOURCES_PATH / "logs"
CHECKPOINT_PATH = RESOURCES_PATH / "checkpoints"
RUNTIME_SETTINGS_FILE = RESOURCES_PATH / "runtime-settings.json"
ENV_FILE_PATH = SETTINGS_DIR / ".env"
ENV_EXAMPLE_FILE_PATH = SETTINGS_DIR / ".env.example"
DATABASE_PATH = RESOURCES_PATH / "database.db"
CLIENT_DIST_PATH = CLIENT_DIR / "dist"
CLIENT_ASSETS_PATH = CLIENT_DIST_PATH / "assets"
CLIENT_INDEX_FILE_PATH = CLIENT_DIST_PATH / "index.html"

CHECKPOINT_CONFIGURATION_DIRNAME = "configuration"
CHECKPOINT_CONFIGURATION_FILE_NAME = "configuration.json"
CHECKPOINT_SESSION_HISTORY_FILE_NAME = "session_history.json"
CHECKPOINT_REPLAY_MEMORY_FILE_NAME = "replay_memory.pkl"
CHECKPOINT_SAVED_MODEL_FILE_NAME = "saved_model.keras"
CHECKPOINT_STRATEGY_MODEL_FILE_NAME = "strategy.keras"
CHECKPOINT_COMPLETE_FILE_NAME = ".complete"

###############################################################################
def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)

###############################################################################
def configure_runtime_paths(data_dir: str | Path | None = None) -> None:
    """Resolve mutable runtime paths after environment loading."""
    global CHECKPOINT_PATH, DATABASE_PATH, DATA_DIR, LOGS_PATH, RESOURCES_PATH
    global RUNTIME_SETTINGS_FILE

    configured = str(data_dir).strip() if data_dir is not None else ""
    configured_data_dir = Path(configured).expanduser().resolve() if configured else None
    if configured_data_dir is not None and _paths_overlap(configured_data_dir, CACHE_PATH):
        raise ValueError(
            "FAIRS_DATA_DIR must not overlap the canonical disposable cache root "
            f"'{CACHE_PATH}'. Choose a persistent data directory outside runtimes/cache."
        )

    DATA_DIR = configured_data_dir
    RESOURCES_PATH = DATA_DIR if DATA_DIR is not None else APP_DIR / "resources"
    LOGS_PATH = RESOURCES_PATH / "logs"
    CHECKPOINT_PATH = RESOURCES_PATH / "checkpoints"
    RUNTIME_SETTINGS_FILE = RESOURCES_PATH / "runtime-settings.json"
    DATABASE_PATH = RESOURCES_PATH / "database.db"

###############################################################################
def as_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)

###############################################################################
def checkpoint_directory(checkpoint_name: str) -> Path:
    return CHECKPOINT_PATH / checkpoint_name

###############################################################################
def checkpoint_configuration_dir(checkpoint_path: str | Path) -> Path:
    return as_path(checkpoint_path) / CHECKPOINT_CONFIGURATION_DIRNAME

###############################################################################
def checkpoint_configuration_file(checkpoint_path: str | Path) -> Path:
    return (
        checkpoint_configuration_dir(checkpoint_path)
        / CHECKPOINT_CONFIGURATION_FILE_NAME
    )

###############################################################################
def checkpoint_session_history_file(checkpoint_path: str | Path) -> Path:
    return (
        checkpoint_configuration_dir(checkpoint_path)
        / CHECKPOINT_SESSION_HISTORY_FILE_NAME
    )

###############################################################################
def checkpoint_replay_memory_file(checkpoint_path: str | Path) -> Path:
    return (
        checkpoint_configuration_dir(checkpoint_path)
        / CHECKPOINT_REPLAY_MEMORY_FILE_NAME
    )

###############################################################################
def checkpoint_saved_model_file(checkpoint_path: str | Path) -> Path:
    return as_path(checkpoint_path) / CHECKPOINT_SAVED_MODEL_FILE_NAME

###############################################################################
def checkpoint_strategy_model_file(
    checkpoint_path: str | Path,
    filename: str = CHECKPOINT_STRATEGY_MODEL_FILE_NAME,
) -> Path:
    return as_path(checkpoint_path) / filename
