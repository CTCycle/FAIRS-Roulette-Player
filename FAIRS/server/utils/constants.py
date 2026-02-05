from __future__ import annotations

from collections.abc import Callable
from os.path import abspath, join

# [PATHS]
###############################################################################
ROOT_DIR = abspath(join(__file__, "../../../.."))
PROJECT_DIR = join(ROOT_DIR, "FAIRS")
SETTING_PATH = join(PROJECT_DIR, "settings")
RESOURCES_PATH = join(PROJECT_DIR, "resources")
DATA_PATH = join(RESOURCES_PATH, "database")
LOGS_PATH = join(RESOURCES_PATH, "logs")
ENV_FILE_PATH = join(SETTING_PATH, ".env")
DATABASE_FILENAME = "sqlite.db"

###############################################################################
CONFIGURATIONS_FILE = join(SETTING_PATH, "configurations.json")

# [FASTAPI]
###############################################################################
FASTAPI_TITLE = "FAIRS Roulette Backend"
FASTAPI_DESCRIPTION = "FastAPI backend"
FASTAPI_VERSION = "1.0.0"

# [ENDPOINS]
###############################################################################
BASE_URL = "/base/tags"

# [EXTERNAL DATA SOURCES]
###############################################################################
CONSTANT = 1.0

# [DATABASE TABLES]
###############################################################################
ROULETTE_SERIES_TABLE = "ROULETTE_SERIES"
INFERENCE_CONTEXT_TABLE = "INFERENCE_CONTEXT"
GAME_SESSIONS_TABLE = "GAME_SESSIONS"

# [DATABASE COLUMNS]
###############################################################################
ROULETTE_SERIES_COLUMNS = [
    "id",
    "dataset_name",
    "extraction",
    "color",
    "color_code",
    "position",
]
INFERENCE_CONTEXT_COLUMNS = ["id", "dataset_name", "extraction", "uploaded_at"]
GAME_SESSIONS_COLUMNS = [
    "id",
    "session_id",
    "step_index",
    "dataset_name",
    "checkpoint",
    "initial_capital",
    "bet_amount",
    "predicted_action",
    "predicted_action_desc",
    "predicted_confidence",
    "observed_extraction",
    "reward",
    "capital_after",
    "timestamp",
]

# [TRAINING CONSTANTS]
###############################################################################
NUMBERS: int = 37
STATES: int = 47
PAD_VALUE: int = -1
CHECKPOINT_PATH = join(RESOURCES_PATH, "checkpoints")
