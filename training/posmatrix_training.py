import os
import sys
import pickle
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import OneHotEncoder
from keras.utils.vis_utils import plot_model

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
from components.model_assets import NumMatrixModel, RealTimeHistory, ModelTraining
import components.global_paths as globpt
import configurations as cnf

# specify relative paths from global paths and create subfolders
#------------------------------------------------------------------------------
cp_path = os.path.join(globpt.train_path, 'checkpoints')
pred_path = os.path.join(globpt.inference_path, 'predictions')
os.mkdir(cp_path) if not os.path.exists(cp_path) else None
os.mkdir(pred_path) if not os.path.exists(pred_path) else None

# [DATA PREPROCESSING]
#==============================================================================
# ...
#==============================================================================
print(f'''
-------------------------------------------------------------------------------
FAIRS Training
-------------------------------------------------------------------------------
Leverage large volume of roulette extraction data to train the FAIRS CC Model
and predict future extractions based on the observed timeseries 
''')

# Load extraction history data from the .csv datasets in the dataset folder
#------------------------------------------------------------------------------
filepath = os.path.join(globpt.data_path, 'FAIRS_dataset.csv')                
df_FAIRS = pd.read_csv(filepath, sep= ';', encoding='utf-8')

# Sample a subset from the main dataset
#------------------------------------------------------------------------------
num_samples = int(df_FAIRS.shape[0] * cnf.data_size)
df_FAIRS = df_FAIRS[(df_FAIRS.shape[0] - num_samples):]

# add number positions, map numbers to roulette color and reshape dataset
#------------------------------------------------------------------------------
print(f'''STEP 1 -----> Preprocess data for FAIRS training
''')
preprocessor = PreProcessing()
categories = [sorted([x for x in df_FAIRS['timeseries'].unique()])]
df_FAIRS = preprocessor.roulette_positions(df_FAIRS)
df_FAIRS = preprocessor.roulette_colormapping(df_FAIRS, no_mapping=True)
ext_timeseries = pd.DataFrame(df_FAIRS['encoding'].values.reshape(-1, 1), columns=['encoding'])
pos_timeseries = df_FAIRS['position'] 

# split dataset into train and test and generate window-dataset
#------------------------------------------------------------------------------
trainext, testext = preprocessor.split_timeseries(ext_timeseries, cnf.test_size, inverted=cnf.invert_test)   
trainpos, testpos = preprocessor.split_timeseries(pos_timeseries, cnf.test_size, inverted=cnf.invert_test)   
train_samples, test_samples = trainext.shape[0], testext.shape[0]
X_train_ext, Y_train_ext = preprocessor.timeseries_labeling(trainext, cnf.window_size) 
X_train_pos, _ = preprocessor.timeseries_labeling(trainext, cnf.window_size)
X_test_ext, Y_test_ext = preprocessor.timeseries_labeling(testext, cnf.window_size)  
X_test_pos, _ = preprocessor.timeseries_labeling(testext, cnf.window_size)

# one hot encode the output for softmax training shape = (timesteps, features)
#------------------------------------------------------------------------------
print('''STEP 2 -----> One-Hot encode timeseries labels (Y data)
''')
OH_encoder = OneHotEncoder(sparse=False)
Y_train_OHE = OH_encoder.fit_transform(Y_train_ext.reshape(Y_train_ext.shape[0], -1))
Y_test_OHE = OH_encoder.transform(Y_test_ext.reshape(Y_test_ext.shape[0], -1))
 
# [SAVE FILES]
#==============================================================================
# Save the trained preprocessing systems (normalizer and encoders) for further use 
#==============================================================================
print('''STEP 3 -----> Save preprocessed data on local hard drive
''')

# create model folder
#------------------------------------------------------------------------------
model_folder_path = preprocessor.model_savefolder(cp_path, 'FAIRSNMM')
model_folder_name = preprocessor.folder_name

# create preprocessing subfolder
#------------------------------------------------------------------------------
pp_path = os.path.join(model_folder_path, 'preprocessing')
os.mkdir(pp_path) if not os.path.exists(pp_path) else None

# save encoder
#------------------------------------------------------------------------------
encoder_path = os.path.join(pp_path, 'OH_encoder.pkl')
with open(encoder_path, 'wb') as file:
    pickle.dump(OH_encoder, file)

# save npy files
#------------------------------------------------------------------------------
np.save(os.path.join(pp_path, 'train_extractions.npy'), X_train_ext)
np.save(os.path.join(pp_path, 'train_positions.npy'), X_train_pos)
np.save(os.path.join(pp_path, 'train_labels.npy'), Y_train_OHE)
np.save(os.path.join(pp_path, 'test_extractions.npy'), X_test_ext)
np.save(os.path.join(pp_path, 'test_positions.npy'), X_test_pos)
np.save(os.path.join(pp_path, 'test_labels.npy'), Y_test_OHE)

# [DEFINE AND BUILD MODEL]
#==============================================================================
# module for the selection of different operations
#==============================================================================
print('''STEP 4 -----> Build the model and start training
''')

trainer = ModelTraining(device=cnf.training_device, seed=cnf.seed, 
                        use_mixed_precision=cnf.use_mixed_precision) 

# initialize model class and build model
#------------------------------------------------------------------------------
modelframe = NumMatrixModel(cnf.learning_rate, cnf.window_size, cnf.embedding_size, 
                            cnf.num_blocks, cnf.num_heads, cnf.kernel_size,  
                            cnf.seed, cnf.XLA_acceleration)
model = modelframe.get_model(summary=True)

# plot model graph
#------------------------------------------------------------------------------
if cnf.generate_model_graph == True:
    plot_path = os.path.join(model_folder_path, 'FAIRSNMM_model.png')       
    plot_model(model, to_file = plot_path, show_shapes = True, 
               show_layer_names = True, show_layer_activations = True, 
               expand_nested = True, rankdir = 'TB', dpi = 400)

# [TRAINING MODEL]
#==============================================================================
# Setting callbacks and training routine for the features extraction model. 
# use command prompt on the model folder and (upon activating environment), 
# use the bash command: python -m tensorboard.main --logdir = tensorboard/
#==============================================================================
most_freq_train = int(trainext.value_counts().idxmax()[0])
most_freq_test = int(testext.value_counts().idxmax()[0])

print(f'''
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
Number of classes in train dataset:   {len(np.unique(X_train_ext))}
Number of classes in test dataset:    {len(np.unique(X_test_ext))}
-------------------------------------------------------------------------------
Number of epochs: {cnf.epochs}
Window size:      {cnf.window_size}
Batch size:       {cnf.batch_size} 
Learning rate:    {cnf.learning_rate} 
-------------------------------------------------------------------------------  
''')

# initialize real time plot callback
#------------------------------------------------------------------------------
RTH_callback = RealTimeHistory(model_folder_path)

# setting for validation data
#------------------------------------------------------------------------------
validation_data = ([X_test_ext, X_test_pos], Y_test_OHE)   

# initialize tensorboard
#------------------------------------------------------------------------------
if cnf.use_tensorboard == True:
    log_path = os.path.join(model_folder_path, 'tensorboard')
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_path, histogram_freq=1)
    callbacks = [RTH_callback, tensorboard_callback]    
else:    
    callbacks = [RTH_callback]

# training loop
#------------------------------------------------------------------------------
multiprocessing = cnf.num_processors > 1
training = model.fit(x=[X_train_ext, X_train_pos], y=Y_train_OHE, batch_size=cnf.batch_size, 
                     validation_data=validation_data, epochs=cnf.epochs, callbacks=callbacks, 
                     workers=cnf.num_processors, use_multiprocessing=multiprocessing)

# save model as savedmodel format
#------------------------------------------------------------------------------
model_file_path = os.path.join(model_folder_path, 'model')
model.save(model_file_path, save_format='tf', save_traces=True)

print(f'''
-------------------------------------------------------------------------------
Training session is over. Model has been saved in folder {model_folder_name}
-------------------------------------------------------------------------------
''')

# save model data and model parameters in txt files
#------------------------------------------------------------------------------
parameters = {'model_name' : 'NMM',
              'train_samples' : train_samples,
              'test_samples' : test_samples,             
              'window_size' : cnf.window_size,              
              'embedding_dimensions' : cnf.embedding_size,
              'num_blocks' : cnf.num_blocks,
              'num_heads' : cnf.num_heads,             
              'batch_size' : cnf.batch_size,
              'learning_rate' : cnf.learning_rate,
              'epochs' : cnf.epochs}

trainer.model_parameters(parameters, model_folder_path)

