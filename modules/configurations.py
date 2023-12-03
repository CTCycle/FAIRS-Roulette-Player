# Define general variables
#------------------------------------------------------------------------------
generate_model_graph = True
use_mixed_precision = True
use_tensorboard = True
XLA_acceleration = False

# Define variables for the training
#------------------------------------------------------------------------------
seed = 42
training_device = 'GPU'
neuron_baseline = 96
epochs = 1200
learning_rate = 0.001
batch_size = 800

# embedding and convolutions
#------------------------------------------------------------------------------
embedding_size = 256

# Define variables for preprocessing
#------------------------------------------------------------------------------
use_test_data = True
invert_test = True
data_size = 1.0
test_size = 0.2
window_size = 100
output_size = 1

# mapping data
#------------------------------------------------------------------------------
categories_mapping = {0 : 'green', 1 : 'black', 2 : 'red'}



