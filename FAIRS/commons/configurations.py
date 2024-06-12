# Advanced settings for training 
# For XLA acceleration you must add XLA_FLAGS: --xla_gpu_cuda_data_dir=path\to\nvvm\folder
#------------------------------------------------------------------------------
MIXED_PRECISION = False
USE_TENSORBOARD = False
XLA_ACCELERATION = False
ML_DEVICE = 'GPU'
NUM_PROCESSORS = 6

# Settings for training routine
#------------------------------------------------------------------------------
EPOCHS = 20
LEARNING_RATE = 0.0001
BATCH_SIZE = 512

# Model settings
#------------------------------------------------------------------------------
EMBEDDING_SIZE = 128
KERNEL_SIZE = 6
NUM_BLOCKS = 3
NUM_HEADS = 3
SAVE_MODEL_PLOT = True

# Settings for training data 
#------------------------------------------------------------------------------
INVERT_TEST = False
DATA_SIZE = 1.0
TEST_SIZE = 0.1
WINDOW_SIZE = 30

# Other settings
#------------------------------------------------------------------------------
SEED = 514
PREDICTIONS_SIZE = 1000
CATEGORIES_MAPPING = {0 : 'green',
                      1 : 'black', 
                      2 : 'red'}