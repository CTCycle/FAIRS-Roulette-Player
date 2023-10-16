import os

# Define paths
#------------------------------------------------------------------------------
data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dataset')
model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model')
GCM_model_path = os.path.join(model_path, 'GCM model')
GCM_data_path = os.path.join(data_path, 'GCM data')
FEM_model_path = os.path.join(model_path, 'FEM model')
FEM_data_path = os.path.join(data_path, 'FEM data')

# Create folders
#------------------------------------------------------------------------------
if not os.path.exists(data_path):
    os.mkdir(data_path)
if not os.path.exists(model_path):
    os.mkdir(model_path)
if not os.path.exists(GCM_model_path):
    os.mkdir(GCM_model_path) 
if not os.path.exists(GCM_data_path):
    os.mkdir(GCM_data_path)  
if not os.path.exists(FEM_model_path):
    os.mkdir(FEM_model_path) 
if not os.path.exists(FEM_data_path):
    os.mkdir(FEM_data_path)  


# Define general variables
#------------------------------------------------------------------------------
generate_model_graph = True

# Define variables for the training
#------------------------------------------------------------------------------
seed = 42
training_device = 'GPU'
epochs = 400
learning_rate = 0.0001
batch_size = 400

# Define variables for preprocessing
#------------------------------------------------------------------------------
data_size = 1.0
test_size = 0.1
window_size = 60




