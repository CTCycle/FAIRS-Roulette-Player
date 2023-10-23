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
embedding_size = 512
epochs = 2000
learning_rate = 0.0001
batch_size = 512

# Define variables for preprocessing
#------------------------------------------------------------------------------
data_size = 1.0
test_size = 0.1
window_size = 128




