import os
import sys
import numpy as np
import pandas as pd


# set warnings
#------------------------------------------------------------------------------
import warnings
warnings.simplefilter(action='ignore', category = Warning)

# add parent folder path to the namespace
#------------------------------------------------------------------------------
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 

# import modules and components
#------------------------------------------------------------------------------
from components.data_assets import PreProcessing
from components.model_assets import RealTimeHistory, ModelTraining, ModelValidation
import components.global_paths as globpt
import configurations as cnf

# specify relative paths from global paths and create subfolders
#------------------------------------------------------------------------------
analysis_path = os.path.join(globpt.data_path, 'analysis')
os.mkdir(analysis_path) if not os.path.exists(analysis_path) else None



# [LOAD DATASETS]
#==============================================================================
# Load patient dataset and dictionaries from .csv files in the dataset folder.
# Also, create a clean version of the exploded dataset to work on
#==============================================================================
filepath = os.path.join(globpt.data_path, 'FAIRS_dataset.csv')                
df_FAIRS = pd.read_csv(filepath, sep= ';', encoding='utf-8')
num_samples = int(df_FAIRS.shape[0] * cnf.data_size)
df_FAIRS = df_FAIRS[(df_FAIRS.shape[0] - num_samples):]

