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
neuron_baseline = 128
embedding_size = 512
epochs = 1000
learning_rate = 0.001
batch_size = 512

# Define variables for preprocessing
#------------------------------------------------------------------------------
use_test_data = True
invert_test = True
data_size = 1.0
test_size = 0.1
window_size = 64
output_size = 4

# mapping data
#------------------------------------------------------------------------------
categories_mapping = {0 : 'green', 1 : 'black', 2 : 'red'}



