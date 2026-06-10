from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
APP_DIR = ROOT_DIR / "app"
SERVER_DIR = APP_DIR / "server"
CLIENT_DIR = APP_DIR / "client"
SETTINGS_DIR = ROOT_DIR / "settings"
RESOURCES_PATH = APP_DIR / "resources"
LOGS_PATH = RESOURCES_PATH / "logs"
CHECKPOINT_PATH = RESOURCES_PATH / "checkpoints"
ENV_FILE_PATH = SETTINGS_DIR / ".env"
CONFIGURATIONS_FILE = SETTINGS_DIR / "configurations.json"
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
