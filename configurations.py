# Define general variables
#------------------------------------------------------------------------------
generate_model_graph = True
use_mixed_precision = True
use_tensorboard = False
XLA_acceleration = False

# Define variables for the training
#------------------------------------------------------------------------------
seed = 42
training_device = 'GPU'
epochs = 10
learning_rate = 0.0001
batch_size = 512

# embedding and convolutions
#------------------------------------------------------------------------------
embedding_size = 128
kernel_size = 6
num_blocks = 3
num_heads = 3

# Define variables for preprocessing
#------------------------------------------------------------------------------
use_test_data = True
invert_test = False
data_size = 1.0
test_size = 0.1
window_size = 25
output_size = 1

# Predictions variables
#------------------------------------------------------------------------------
predictions_size = 2000

# mapping data
#------------------------------------------------------------------------------
categories_mapping = {0 : 'green', 1 : 'black', 2 : 'red'}



