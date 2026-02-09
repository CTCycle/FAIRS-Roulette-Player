from __future__ import annotations

from collections.abc import Callable
from os.path import abspath, join

# [PATHS]
###############################################################################
ROOT_DIR = abspath(join(__file__, "../../../.."))
PROJECT_DIR = join(ROOT_DIR, "FAIRS")
SETTING_PATH = join(PROJECT_DIR, "settings")
RESOURCES_PATH = join(PROJECT_DIR, "resources")
LOGS_PATH = join(RESOURCES_PATH, "logs")
ENV_FILE_PATH = join(SETTING_PATH, ".env")
DATABASE_FILENAME = "database.db"

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
ROULETTE_SERIES_TABLE = "roulette_series"
INFERENCE_CONTEXT_TABLE = "inference_context"
GAME_SESSIONS_TABLE = "game_sessions"

# [DATABASE COLUMNS]
###############################################################################
ROULETTE_SERIES_COLUMNS = [
    "id",
    "name",
    "outcome",
    "color",
    "color_code",
    "position",
]
INFERENCE_CONTEXT_COLUMNS = ["id", "name", "outcome", "uploaded_at"]
GAME_SESSIONS_COLUMNS = [
    "id",
    "session_id",
    "step_id",
    "name",
    "checkpoint",
    "initial_capital",
    "bet_amount",
    "predicted_action",
    "predicted_action_desc",
    "predicted_confidence",
    "observed_outcome",
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
