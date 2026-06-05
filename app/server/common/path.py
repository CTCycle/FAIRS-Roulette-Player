from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
APP_DIR = ROOT_DIR / "app"
SERVER_DIR = APP_DIR / "server"
SETTINGS_DIR = ROOT_DIR / "settings"
RESOURCES_PATH = APP_DIR / "resources"
LOGS_PATH = RESOURCES_PATH / "logs"
CHECKPOINT_PATH = RESOURCES_PATH / "checkpoints"
ENV_FILE_PATH = SETTINGS_DIR / ".env"
CONFIGURATIONS_FILE = SETTINGS_DIR / "configurations.json"
DATABASE_FILENAME = "database.db"
DATABASE_PATH = RESOURCES_PATH / DATABASE_FILENAME
CLIENT_DIST_PATH = APP_DIR / "client" / "dist"
CLIENT_ASSETS_PATH = CLIENT_DIST_PATH / "assets"
CLIENT_INDEX_FILE_PATH = CLIENT_DIST_PATH / "index.html"
