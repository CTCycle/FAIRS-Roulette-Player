# Define general variables
#------------------------------------------------------------------------------
generate_model_graph = True
use_mixed_precision = True
use_tensorboard = False
XLA_acceleration = False

# Define variables for the training
#------------------------------------------------------------------------------
seed = 76
training_device = 'GPU'
embedding_size = 512
epochs = 2000
learning_rate = 0.00001
batch_size = 512

# Define variables for preprocessing
#------------------------------------------------------------------------------
use_test_data = True
data_size = 1.0
test_size = 0.2
window_size = 96




