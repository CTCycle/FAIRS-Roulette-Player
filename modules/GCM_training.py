import os
import sys
import numpy as np
import pandas as pd
import pickle
import tensorflow as tf
from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder
from keras.utils.vis_utils import plot_model
import warnings
warnings.simplefilter(action='ignore', category = Warning)

# [IMPORT MODULES AND CLASSES]
#==============================================================================
if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from modules.components.data_classes import PreProcessing
from modules.components.training_classes import GroupedClassModel, RealTimeHistory, ModelTraining, ModelValidation
import modules.global_variables as GlobVar

# [LOAD DATASETS]
#==============================================================================
# Load patient dataset and dictionaries from .csv files in the dataset folder.
# Also, create a clean version of the exploded dataset to work on
#==============================================================================
filepath = os.path.join(GlobVar.data_path, 'FAIRS_dataset.csv')                
df_FAIRS = pd.read_csv(filepath, sep= ';', encoding='utf-8')

num_samples = int(df_FAIRS.shape[0] * GlobVar.data_size)
df_FAIRS = df_FAIRS[(df_FAIRS.shape[0] - num_samples):]
        
print(f'''
-------------------------------------------------------------------------------
FAIRS Training
-------------------------------------------------------------------------------
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus. Suspendisse 
lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed, dolor. Cras elementum 
ultrices diam. Maecenas ligula massa, varius a, semper congue, euismod non, mi. 
Proin porttitor, orci nec nonummy molestie, enim est eleifend mi, non fermentum diam 
nisl sit amet erat. Duis semper. Duis arcu massa, scelerisque vitae, consequat in, pretium a, enim. 
''')

# [COLOR MAPPING AND ENCODING]
#==============================================================================
# ...
#==============================================================================
print(f'''
-------------------------------------------------------------------------------
Data preprocessing
-------------------------------------------------------------------------------
...
''')

# map numbers to roulette color and reshape dataset
#------------------------------------------------------------------------------
preprocessor = PreProcessing()
df_FAIRS = preprocessor.roulette_colormapping(df_FAIRS)
FAIRS_categorical = df_FAIRS['color encoding']
FAIRS_categorical = FAIRS_categorical.values.reshape(-1, 1)

# encode series from string to number class for the inputs
#------------------------------------------------------------------------------
categories = [['green', 'black', 'red']]
categorical_encoder = OrdinalEncoder(categories = categories, handle_unknown = 'use_encoded_value', unknown_value=-1)
FAIRS_categorical = categorical_encoder.fit_transform(FAIRS_categorical)
FAIRS_categorical = pd.DataFrame(FAIRS_categorical, columns=['color encoding'])

# [SEPARATE DATASETS AND GENERATE TIMESTEPS WINDOWS]
#==============================================================================
# ...
#==============================================================================
print('''STEP 1 -----> Separate datasets and generate time windows
''')

# split dataset into train and test
#------------------------------------------------------------------------------
categorical_train, categorical_test = preprocessor.split_timeseries(FAIRS_categorical, GlobVar.test_size, inverted=False)

# generate windowed dataset
#------------------------------------------------------------------------------
X_train, Y_train, X_test, Y_test = preprocessor.timeseries_labeling(categorical_train, categorical_test, GlobVar.window_size)

# [ONE HOT ENCODE THE LABELS]
#==============================================================================
# ...
#==============================================================================
print('''STEP 2 -----> One Hot Encode the labels
''')

# one hot encode the output for softmax training (3 classes)
#------------------------------------------------------------------------------
OH_encoder = OneHotEncoder(sparse=False)
Y_train_OHE = OH_encoder.fit_transform(Y_train)
Y_test_OHE = OH_encoder.fit_transform(Y_test)

# [SAVE FILES]
#==============================================================================
# Save the trained preprocessing systems (normalizer and encoders) for further use 
#==============================================================================
print('''STEP 3 -----> Save files
''')

# save encoder
#------------------------------------------------------------------------------
encoder_path = os.path.join(GlobVar.GCM_data_path, 'categorical_encoder.pkl')
with open(encoder_path, 'wb') as file:
    pickle.dump(categorical_encoder, file) 

# reshape and transform into dataframe (categorical dataset)
#------------------------------------------------------------------------------
X_train = X_train.reshape(X_train.shape[0], -1)
X_test = X_test.reshape(X_test.shape[0], -1)
Y_train = Y_train.reshape(Y_train.shape[0], -1)
Y_test = Y_test.reshape(Y_test.shape[0], -1)

# create pd dataframe from files
#------------------------------------------------------------------------------
df_X_train = pd.DataFrame(X_train)
df_X_test = pd.DataFrame(X_test)
df_Y_train_OHE = pd.DataFrame(Y_train_OHE)
df_Y_test_OHE = pd.DataFrame(Y_test_OHE)

# save csv files
#------------------------------------------------------------------------------
file_loc = os.path.join(GlobVar.GCM_data_path, 'GCM_preprocessed.xlsx')  
writer = pd.ExcelWriter(file_loc, engine='xlsxwriter')
df_X_train.to_excel(writer, sheet_name='train inputs', index=True)
df_X_test.to_excel(writer, sheet_name='test inputs', index=True)
df_Y_train_OHE.to_excel(writer, sheet_name='train labels', index=True)
df_Y_test_OHE.to_excel(writer, sheet_name='test labels', index=True)
writer.close()

# [REPORT]
#==============================================================================
# ....
#==============================================================================
print(f'''
-------------------------------------------------------------------------------
Classes are encoded as following
-------------------------------------------------------------------------------
green = 0
black = 1
red =   2
-------------------------------------------------------------------------------   
number of timepoints in train dataset: {categorical_train.shape[0]}
number of timepoints in test dataset:  {categorical_test.shape[0]}
most frequent class in train dataset:  {int(categorical_train['color encoding'].value_counts().idxmax())}
most frequent class in test dataset:   {int(categorical_test['color encoding'].value_counts().idxmax())}
''')

# [DEFINE AND BUILD MODEL]
#==============================================================================
# module for the selection of different operations
#==============================================================================
print('''STEP 4 -----> Build the model and start training
''')
trainworker = ModelTraining(device = GlobVar.training_device) 
model_savepath = preprocessor.model_savefolder(GlobVar.GCM_model_path, 'FAIRSGCM')

# initialize model class
#------------------------------------------------------------------------------
modelframe = GroupedClassModel(GlobVar.learning_rate, GlobVar.window_size, output_size=3)
model = modelframe.build()
model.summary(expand_nested=True)

# plot model graph
#------------------------------------------------------------------------------
if GlobVar.generate_model_graph == True:
    plot_path = os.path.join(model_savepath, 'FAIRSGCM_model.png')       
    plot_model(model, to_file = plot_path, show_shapes = True, 
                show_layer_names = True, show_layer_activations = True, 
                expand_nested = True, rankdir = 'TB', dpi = 400)

# [TRAINING WITH FAIRS]
#==============================================================================
# Setting callbacks and training routine for the features extraction model. 
# use command prompt on the model folder and (upon activating environment), 
# use the bash command: python -m tensorboard.main --logdir = tensorboard/
#==============================================================================
log_path = os.path.join(model_savepath, 'tensorboard')
tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_path, histogram_freq=1)
RTH_callback = RealTimeHistory(model_savepath, validation=True)

# training loop and model saving at end
#------------------------------------------------------------------------------
print(f'''Start model training for {GlobVar.epochs} epochs and batch size of {GlobVar.batch_size}
       ''')
training = model.fit(x=X_train, y=Y_train_OHE, batch_size=GlobVar.batch_size, 
                     validation_data=(X_test, Y_test_OHE), 
                     epochs = GlobVar.epochs, callbacks = [RTH_callback, tensorboard_callback],
                     workers = 6, use_multiprocessing=True)

model.save(model_savepath)

# [MODEL VALIDATION]
#==============================================================================
# ...
#==============================================================================
print('''STEP 5 -----> Evaluate the model
''')
categories_mapping = {0 : 'green', 1 : 'black', 2 : 'red'}

validator = ModelValidation()
predicted_train_timeseries = model.predict(X_train)
predicted_test_timeseries = model.predict(X_test)

y_pred_labels = np.argmax(predicted_train_timeseries, axis=1)
y_true_labels = np.argmax(Y_train_OHE, axis=1)
validator.FAIRS_confusion(y_true_labels, y_pred_labels, categories[0], 'train', model_savepath, 400)
#validator.FAIRS_ROC_curve(y_true_labels, y_pred_labels, categories_mapping, 'train', model_savepath, 400)

y_pred_labels = np.argmax(predicted_test_timeseries, axis=1)
y_true_labels = np.argmax(Y_test_OHE, axis=1)
validator.FAIRS_confusion(y_true_labels, y_pred_labels, categories[0], 'test', model_savepath, 400)
#validator.FAIRS_ROC_curve(y_true_labels, y_pred_labels, categories_mapping, 'test', model_savepath, 400)





