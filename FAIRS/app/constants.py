import json
from os.path import join, abspath 

# [PATHS]
###############################################################################
ROOT_DIR = abspath(join(__file__, "../../.."))
PROJECT_DIR = join(ROOT_DIR, 'FAIRS')
RSC_PATH = join(PROJECT_DIR, 'resources')
DATA_PATH = join(RSC_PATH, 'database')
SOURCE_PATH = join(DATA_PATH, 'dataset')
METADATA_PATH = join(DATA_PATH, 'metadata')
INFERENCE_PATH = join(DATA_PATH, 'inference')
EVALUATION_PATH = join(DATA_PATH, 'validation')
CHECKPOINT_PATH = join(RSC_PATH, 'checkpoints')
CONFIG_PATH = join(RSC_PATH, 'configurations')
LOGS_PATH = join(RSC_PATH, 'logs')

# files
###############################################################################
PROCESS_METADATA_FILE = join(METADATA_PATH, 'preprocessing_metadata.json')

# [CONFIGURATIONS]
###############################################################################
NUMBERS = 37
STATES = 47
PAD_VALUE = -1

# [UI LAYOUT PATH]
###############################################################################
UI_PATH = join(PROJECT_DIR, 'app', 'assets', 'window_layout.ui')

CONFIG_PATH = join(PROJECT_DIR, 'settings', 'configurations.json')
with open(CONFIG_PATH, 'r') as file:
    CONFIG = json.load(file)

