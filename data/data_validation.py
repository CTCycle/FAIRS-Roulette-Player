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
from utils.data_assets import PreProcessing
from utils.model_assets import RealTimeHistory, ModelTraining, ModelValidation
import utils.global_paths as globpt
import configurations as cnf

# specify relative paths from global paths and create subfolders
#------------------------------------------------------------------------------
analysis_path = os.path.join(globpt.data_path, 'analysis')
os.mkdir(analysis_path) if not os.path.exists(analysis_path) else None

# [LOAD AND PREPROCESS DATA]
#==============================================================================
#==============================================================================
filepath = os.path.join(globpt.data_path, 'FAIRS_dataset.csv')                
df_FAIRS = pd.read_csv(filepath, sep= ';', encoding='utf-8')
num_samples = int(df_FAIRS.shape[0] * cnf.data_size)
df_FAIRS = df_FAIRS[(df_FAIRS.shape[0] - num_samples):]

preprocessor = PreProcessing()

# add number positions, map numbers to roulette color and reshape dataset
#------------------------------------------------------------------------------
categories = [['green', 'black', 'red']]
categorical_encoder = OrdinalEncoder(categories=categories, handle_unknown='use_encoded_value', unknown_value=-1)
df_FAIRS = preprocessor.roulette_colormapping(df_FAIRS, no_mapping=False)
timeseries = categorical_encoder.fit_transform(df_FAIRS['encoding'].values.reshape(-1, 1))
timeseries = pd.DataFrame(timeseries, columns=['encoding'])

# split dataset into train and test and generate window-dataset
#------------------------------------------------------------------------------
train_data, test_data = preprocessor.split_timeseries(timeseries, cnf.test_size, inverted=cnf.invert_test)   
train_samples, test_samples = train_data.shape[0], test_data.shape[0]
X_train, Y_train = preprocessor.timeseries_labeling(train_data, cnf.window_size) 
X_test, Y_test = preprocessor.timeseries_labeling(test_data, cnf.window_size)   

# one hot encode the output for softmax training shape = (timesteps, features)
#------------------------------------------------------------------------------
print('''One-Hot encode timeseries labels (Y data)\n''')
OH_encoder = OneHotEncoder(sparse=False)
Y_train_OHE = OH_encoder.fit_transform(Y_train.reshape(Y_train.shape[0], -1))
Y_test_OHE = OH_encoder.transform(Y_test.reshape(Y_test.shape[0], -1))


