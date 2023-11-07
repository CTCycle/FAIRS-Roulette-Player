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
neuron_baseline = 96
embedding_size = 512
epochs = 5000
learning_rate = 0.0001
batch_size = 512

# Define variables for preprocessing
#------------------------------------------------------------------------------
use_test_data = True
data_size = 1.0
test_size = 0.04
window_size = 120
output_size = 2

# mapping data
#------------------------------------------------------------------------------
categories_mapping = {0 : 'green', 1 : 'black', 2 : 'red'}



