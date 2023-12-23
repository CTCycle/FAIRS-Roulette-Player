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
epochs = 1000
learning_rate = 0.001
batch_size = 1440

# embedding and convolutions
#------------------------------------------------------------------------------
embedding_size = 256
kernel_size = 6

# Define variables for preprocessing
#------------------------------------------------------------------------------
use_test_data = True
invert_test = False
data_size = 1.0
test_size = 0.2
window_size = 60
output_size = 1

# k fold training
#------------------------------------------------------------------------------
k_fold = 4
k_epochs = 1500

# Predictions variables
#------------------------------------------------------------------------------
predictions_size = 2000

# mapping data
#------------------------------------------------------------------------------
categories_mapping = {0 : 'green', 1 : 'black', 2 : 'red'}



