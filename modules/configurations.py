# Define general variables
#------------------------------------------------------------------------------
generate_model_graph = True
use_mixed_precision = True
use_tensorboard = False
XLA_acceleration = False

# Define variables for the training
#------------------------------------------------------------------------------
seed = 52
training_device = 'GPU'
neuron_baseline = 128
epochs = 200
learning_rate = 0.00005
batch_size = 512

# embedding and convolutions
#------------------------------------------------------------------------------
embedding_size = 512
kernel_size = 32

# Define variables for preprocessing
#------------------------------------------------------------------------------
use_test_data = True
invert_test = False
data_size = 1.0
test_size = 0.1
window_size = 100
output_size = 1

# mapping data
#------------------------------------------------------------------------------
color_encoding = False
categories_mapping = {0 : 'green', 1 : 'black', 2 : 'red'}



