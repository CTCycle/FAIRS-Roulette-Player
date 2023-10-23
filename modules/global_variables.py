import os

# Define paths
#------------------------------------------------------------------------------
data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dataset')
model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model')
CCM_model_path = os.path.join(model_path, 'CCM model')
CCM_data_path = os.path.join(data_path, 'CCM data')


# Create folders
#------------------------------------------------------------------------------
if not os.path.exists(data_path):
    os.mkdir(data_path)
if not os.path.exists(model_path):
    os.mkdir(model_path)
if not os.path.exists(CCM_model_path):
    os.mkdir(CCM_model_path) 
if not os.path.exists(CCM_data_path):
    os.mkdir(CCM_data_path)  


