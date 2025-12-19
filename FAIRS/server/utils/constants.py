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
SERVER_CONFIGURATION_FILE = join(SETTING_PATH, "server_configurations.json")

# [ENDPOINS]
###############################################################################
BASE_URL = "/base/tags"

# [EXTERNAL DATA SOURCES]
###############################################################################
CONSTANT = 1.0

# [DATABASE TABLES]
###############################################################################
ROULETTE_SERIES_TABLE = "ROULETTE_SERIES"
PREDICTED_GAMES_TABLE = "PREDICTED_GAMES"
CHECKPOINTS_SUMMARY_TABLE = "CHECKPOINTS_SUMMARY"

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
PREDICTED_GAMES_COLUMNS = ["id", "checkpoint", "extraction", "predicted_action"]
CHECKPOINTS_SUMMARY_COLUMNS = [
    "checkpoint",
    "sample_size",
    "seed",
    "precision",
    "episodes",
    "max_steps_episode",
    "batch_size",
    "jit_compile",
    "has_tensorboard_logs",
    "learning_rate",
    "neurons",
    "embedding_dimensions",
    "perceptive_field_size",
    "exploration_rate",
    "exploration_rate_decay",
    "discount_rate",
    "model_update_frequency",
    "loss",
    "accuracy",
]

# [TRAINING CONSTANTS]
###############################################################################
NUMBERS: int = 37
STATES: int = 47
PAD_VALUE: int = -1
CHECKPOINT_PATH = join(RESOURCES_PATH, "checkpoints")
