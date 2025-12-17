from __future__ import annotations

from os.path import abspath, join

# [PATHS]
###############################################################################
ROOT_DIR = abspath(join(__file__, "../../../.."))
PROJECT_DIR = join(ROOT_DIR, "FAIRS")
RESOURCES_PATH = join(PROJECT_DIR, "resources")
DATA_PATH = join(RESOURCES_PATH, "database")
SOURCE_PATH = join(DATA_PATH, "dataset")
METADATA_PATH = join(DATA_PATH, "metadata")
INFERENCE_PATH = join(DATA_PATH, "inference")
EVALUATION_PATH = join(DATA_PATH, "validation")
CHECKPOINT_PATH = join(RESOURCES_PATH, "checkpoints")
CONFIG_PATH = join(RESOURCES_PATH, "configurations")
LOGS_PATH = join(RESOURCES_PATH, "logs")
PROCESS_METADATA_FILE = join(METADATA_PATH, "preprocessing_metadata.json")

# [CONFIGURATIONS]
###############################################################################
NUMBERS: int = 37
STATES: int = 47
PAD_VALUE: int = -1

# [UI LAYOUT PATH]
###############################################################################
UI_PATH = join(PROJECT_DIR, "app", "layout", "main_window.ui")
