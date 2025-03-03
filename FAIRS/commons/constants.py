import json
from os.path import join, abspath 

# [PATHS]
###############################################################################
ROOT_DIR = abspath(join(__file__, "../../.."))
PROJECT_DIR = abspath(join(__file__, "../.."))
RSC_PATH = join(PROJECT_DIR, 'resources')
DATA_PATH = join(RSC_PATH, 'dataset')
PRED_PATH = join(RSC_PATH, 'predictions')
CHECKPOINT_PATH = join(RSC_PATH, 'checkpoints')
LOGS_PATH = join(PROJECT_DIR, 'resources', 'logs')
DATASET_NAME = 'FAIRS_dataset.csv'



# [CONFIGURATIONS]
###############################################################################
NUMBERS = 37
COLORS = 3
SPECIALS = 1
STATES = NUMBERS + COLORS + SPECIALS - 1

CONFIG_PATH = join(PROJECT_DIR, 'settings', 'configurations.json')
with open(CONFIG_PATH, 'r') as file:
    CONFIG = json.load(file)

