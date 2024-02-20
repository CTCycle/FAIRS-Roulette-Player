# Advanced settings for training 
#------------------------------------------------------------------------------
use_mixed_precision = False
use_tensorboard = False
XLA_acceleration = False
training_device = 'GPU'
num_processors = 6

# Settings for training routine
#------------------------------------------------------------------------------
epochs = 20
learning_rate = 0.0001
batch_size = 512

# Model settings
#------------------------------------------------------------------------------
embedding_size = 128
kernel_size = 6
num_blocks = 3
num_heads = 3
generate_model_graph = True

# Settings for training data 
#------------------------------------------------------------------------------
invert_test = False
data_size = 1.0
test_size = 0.1
window_size = 30

# Other settings
#------------------------------------------------------------------------------
seed = 514
predictions_size = 1000
categories_mapping = {0 : 'green', 1 : 'black', 2 : 'red'}