import json
from os.path import join, abspath 

# [PATHS]
###############################################################################
ROOT_DIR = abspath(join(__file__, "../../.."))
PROJECT_DIR = join(ROOT_DIR, 'FAIRS')
RSC_PATH = join(PROJECT_DIR, 'resources')
DATA_PATH = join(RSC_PATH, 'database')
METADATA_PATH = join(DATA_PATH, 'metadata')
INFERENCE_PATH = join(RSC_PATH, 'inference')
VALIDATION_PATH = join(DATA_PATH, 'validation')
CHECKPOINT_PATH = join(RSC_PATH, 'checkpoints')
LOGS_PATH = join(RSC_PATH, 'logs')

# [CONFIGURATIONS]
###############################################################################
NUMBERS = 37
COLORS = 3
SPECIALS = 1
STATES = NUMBERS + COLORS + SPECIALS - 1

CONFIG_PATH = join(PROJECT_DIR, 'settings', 'configurations.json')
with open(CONFIG_PATH, 'r') as file:
    CONFIG = json.load(file)

