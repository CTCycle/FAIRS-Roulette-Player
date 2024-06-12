from os.path import join, dirname, abspath 

PROJECT_DIR = dirname(dirname(abspath(__file__)))
DATA_PATH = join(PROJECT_DIR, 'data')
CHECKPOINT_PATH = join(PROJECT_DIR, 'training', 'checkpoints')
PREDICTIONS_PATH = join(PROJECT_DIR, 'inference', 'predictions')




