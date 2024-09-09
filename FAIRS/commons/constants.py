import json
from os.path import join, dirname, abspath 

PROJECT_DIR = dirname(dirname(abspath(__file__)))
RSC_PATH = join(PROJECT_DIR, 'resources')
DATA_PATH = join(RSC_PATH, 'dataset')
PP_PATH = join(DATA_PATH, 'preprocessed data')
CHECKPOINT_PATH = join(RSC_PATH, 'checkpoints')
LOGS_PATH = join(PROJECT_DIR, 'resources', 'logs')
DATASET_NAME = 'FAIRS_dataset.csv'

CONFIG_PATH = join(PROJECT_DIR, 'settings', 'configurations.json')
with open(CONFIG_PATH, 'r') as file:
    CONFIG = json.load(file)