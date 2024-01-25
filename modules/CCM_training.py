import os
import sys
import numpy as np
import pandas as pd
import pickle
import tensorflow as tf
from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder
from keras.utils.vis_utils import plot_model

# set warnings
#------------------------------------------------------------------------------
import warnings
warnings.simplefilter(action='ignore', category = Warning)

# add modules path if this file is launched as __main__
#------------------------------------------------------------------------------
if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# import modules and components
#------------------------------------------------------------------------------
from modules.components.data_assets import PreProcessing
from modules.components.model_assets import ColorCodeModel, RealTimeHistory, ModelTraining, ModelValidation
import modules.global_variables as GlobVar
import configurations as cnf

# [LOAD DATASETS]
#==============================================================================
# Load patient dataset and dictionaries from .csv files in the dataset folder.
#==============================================================================
filepath = os.path.join(GlobVar.data_path, 'FAIRS_dataset.csv')                
df_FAIRS = pd.read_csv(filepath, sep= ';', encoding='utf-8')
num_samples = int(df_FAIRS.shape[0] * cnf.data_size)
df_FAIRS = df_FAIRS[(df_FAIRS.shape[0] - num_samples):]

print(f'''
-------------------------------------------------------------------------------
FAIRS Training
-------------------------------------------------------------------------------
Leverage large volume of roulette extraction data to train the FAIRS CC Model
and predict future extractions based on the observed timeseries 
''')

# [COLOR MAPPING AND ENCODING]
#==============================================================================
# ...
#==============================================================================
print(f'''
-------------------------------------------------------------------------------
Data preprocessing
-------------------------------------------------------------------------------
      
STEP 1 -----> Preprocess data for FAIRS training
''')

# add number positions, map numbers to roulette color and reshape dataset
#------------------------------------------------------------------------------
PP = PreProcessing()
categories = [['green', 'black', 'red']]
categorical_encoder = OrdinalEncoder(categories = categories, handle_unknown = 'use_encoded_value', unknown_value=-1)
df_FAIRS = PP.roulette_colormapping(df_FAIRS, no_mapping=False)
timeseries = df_FAIRS['encoding'] 
timeseries = timeseries.values.reshape(-1, 1)       
timeseries = categorical_encoder.fit_transform(timeseries)
timeseries = pd.DataFrame(timeseries, columns=['encoding'])

# split dataset into train and test and generate window-dataset
#------------------------------------------------------------------------------
train_data, test_data = PP.split_timeseries(timeseries, cnf.test_size, inverted=cnf.invert_test)   
train_samples, test_samples = train_data.shape[0], test_data.shape[0]
X_train, Y_train = PP.timeseries_labeling(train_data, cnf.window_size, cnf.output_size) 
X_test, Y_test = PP.timeseries_labeling(test_data, cnf.window_size, cnf.output_size)   

# [ONE HOT ENCODE THE LABELS]
#==============================================================================
# ...
#==============================================================================
print('''STEP 2 -----> One-Hot encode timeseries labels (Y data)
''')

# one hot encode the output for softmax training shape = (timesteps, features)
#------------------------------------------------------------------------------
OH_encoder = OneHotEncoder(sparse=False)
Y_train_OHE = OH_encoder.fit_transform(Y_train.reshape(Y_train.shape[0], -1))
Y_test_OHE = OH_encoder.transform(Y_test.reshape(Y_test.shape[0], -1))

# [SAVE FILES]
#==============================================================================
# Save the trained preprocessing systems (normalizer and encoders) for further use 
#==============================================================================
print('''STEP 3 -----> Save preprocessed data on local hard drive
''')

# create model folder
#------------------------------------------------------------------------------
model_savepath = PP.model_savefolder(GlobVar.model_path, 'FAIRSCCM')
pp_path = os.path.join(model_savepath, 'preprocessing')
if not os.path.exists(pp_path):
    os.mkdir(pp_path)

# save encoder
#------------------------------------------------------------------------------
encoder_path = os.path.join(pp_path, 'categorical_encoder.pkl')
with open(encoder_path, 'wb') as file:
    pickle.dump(categorical_encoder, file)

# save npy files
#------------------------------------------------------------------------------
np.save(os.path.join(pp_path, 'train_data.npy'), X_train)
np.save(os.path.join(pp_path, 'train_labels.npy'), Y_train_OHE)
np.save(os.path.join(pp_path, 'test_data.npy'), X_test)
np.save(os.path.join(pp_path, 'test_labels.npy'), Y_test_OHE)

# [REPORT AND ANALYSIS]
#==============================================================================
# ....
#==============================================================================
most_freq_train = train_data.value_counts().idxmax()
most_freq_test = test_data.value_counts().idxmax()

# [DEFINE AND BUILD MODEL]
#==============================================================================
# module for the selection of different operations
#==============================================================================
print('''STEP 4 -----> Build the model and start training
''')

trainworker = ModelTraining(device=cnf.training_device, seed=cnf.seed, 
                            use_mixed_precision=cnf.use_mixed_precision) 
# initialize model class
#------------------------------------------------------------------------------
modelframe = ColorCodeModel(cnf.learning_rate, cnf.window_size, cnf.output_size, 
                            cnf.embedding_size, cnf.num_blocks, cnf.num_heads, cnf.kernel_size, 
                            seed=cnf.seed, XLA_state=cnf.XLA_acceleration)
model = modelframe.build()
model.summary(expand_nested=True)

# plot model graph
#------------------------------------------------------------------------------
if cnf.generate_model_graph == True:
    plot_path = os.path.join(model_savepath, 'FAIRSCCM_model.png')       
    plot_model(model, to_file = plot_path, show_shapes = True, 
               show_layer_names = True, show_layer_activations = True, 
               expand_nested = True, rankdir = 'TB', dpi = 400)

# [TRAINING WITH FAIRS]
#==============================================================================
# Setting callbacks and training routine for the features extraction model. 
# use command prompt on the model folder and (upon activating environment), 
# use the bash command: python -m tensorboard.main --logdir = tensorboard/
#==============================================================================
print(f'''
-------------------------------------------------------------------------------
TRAINING INFO
-------------------------------------------------------------------------------
Data is encoded by roulette colors: Green as 0, Black as 1, Red as 2
-------------------------------------------------------------------------------
Number of timepoints in train dataset: {train_samples}
Number of timepoints in test dataset:  {test_samples}
-------------------------------------------------------------------------------  
DISTRIBUTION OF CLASSES
-------------------------------------------------------------------------------  
Most frequent class in train dataset: {most_freq_train}
Most frequent class in test dataset:  {most_freq_test}
Number of represented classes in train dataset: {train_data.nunique()}
Number of represented classes in test dataset: {test_data.nunique()}
-------------------------------------------------------------------------------
Number of epochs: {cnf.epochs}
Window size:      {cnf.window_size}
Batch size:       {cnf.batch_size} 
Learning rate:    {cnf.learning_rate} 
-------------------------------------------------------------------------------  
''')

# initialize real time plot callback
#------------------------------------------------------------------------------
RTH_callback = RealTimeHistory(model_savepath)

# setting for validation data
#------------------------------------------------------------------------------
validation_data = (X_test, Y_test_OHE)   

# initialize tensorboard
#------------------------------------------------------------------------------
if cnf.use_tensorboard == True:
    log_path = os.path.join(model_savepath, 'tensorboard')
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_path, histogram_freq=1)
    callbacks = [RTH_callback, tensorboard_callback]    
else:    
    callbacks = [RTH_callback]

# training loop
#------------------------------------------------------------------------------
training = model.fit(x=X_train, y=Y_train_OHE, batch_size=cnf.batch_size, 
                     validation_data=validation_data, epochs=cnf.epochs, 
                     callbacks=callbacks, workers=6, use_multiprocessing=True)


model.save(model_savepath)

# save model data and model parameters in txt files
#------------------------------------------------------------------------------
parameters = {'Model name' : 'NMM',
              'Number of train samples' : train_samples,
              'Number of test samples' : test_samples,             
              'Window size' : cnf.window_size,
              'Output seq length' : cnf.output_size,
              'Embedding dimensions' : cnf.embedding_size,             
              'Batch size' : cnf.batch_size,
              'Learning rate' : cnf.learning_rate,
              'Epochs' : cnf.epochs}

trainworker.model_parameters(parameters, model_savepath)





