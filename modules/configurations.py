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
epochs = 50
learning_rate = 0.001
batch_size = 1020

# embedding and convolutions
#------------------------------------------------------------------------------
embedding_size = 128

# Define variables for preprocessing
#------------------------------------------------------------------------------
use_test_data = True
invert_test = True
data_size = 1.0
test_size = 0.2
window_size = 50
output_size = 1

predictions_size = 1500

# mapping data
#------------------------------------------------------------------------------
categories_mapping = {0 : 'green', 1 : 'black', 2 : 'red'}



