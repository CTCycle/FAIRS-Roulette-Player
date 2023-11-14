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
from modules.components.data_classes import PreProcessing
from modules.components.training_classes import ColorCodeModel, RealTimeHistory, ModelTraining, ModelValidation
import modules.global_variables as GlobVar
import modules.configurations as cnf

# [LOAD DATASETS]
#==============================================================================
# Load patient dataset and dictionaries from .csv files in the dataset folder.
# Also, create a clean version of the exploded dataset to work on
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

# map numbers to roulette color and reshape dataset
#------------------------------------------------------------------------------
PP = PreProcessing()
if cnf.color_encoding == True:
    categories = [['green', 'black', 'red']]
    df_FAIRS = PP.roulette_colormapping(df_FAIRS, no_mapping=False)
    FAIRS_categorical = df_FAIRS['encoding']
    FAIRS_categorical = FAIRS_categorical.values.reshape(-1, 1)    
    categorical_encoder = OrdinalEncoder(categories = categories, handle_unknown = 'use_encoded_value', unknown_value=-1)
    FAIRS_categorical = categorical_encoder.fit_transform(FAIRS_categorical)
    FAIRS_categorical = pd.DataFrame(FAIRS_categorical, columns=['encoding'])
else:    
    df_FAIRS = PP.roulette_colormapping(df_FAIRS, no_mapping=True)
    categories = [sorted([x for x in df_FAIRS['encoding'].unique()])]
    FAIRS_categorical = df_FAIRS['encoding']
    FAIRS_categorical = pd.DataFrame(FAIRS_categorical, columns=['encoding'])
    
# split dataset into train and test and generate window-dataset
#------------------------------------------------------------------------------
if cnf.use_test_data == True:
    trainset, testset = PP.split_timeseries(FAIRS_categorical, cnf.test_size, inverted=cnf.invert_test)
    train_samples, test_samples = trainset.shape[0], testset.shape[0]
    X_train, Y_train = PP.timeseries_labeling(trainset, cnf.window_size, cnf.output_size)
    X_test, Y_test = PP.timeseries_labeling(testset, cnf.window_size, cnf.output_size)
else:
    train_samples, test_samples = FAIRS_categorical.shape[0], 0    
    X_train, Y_train = PP.timeseries_labeling(FAIRS_categorical, cnf.window_size, cnf.output_size)

# [ONE HOT ENCODE THE LABELS]
#==============================================================================
# ...
#==============================================================================
print('''STEP 2 -----> Generate One Hot encoding for labels
''')

# one hot encode the output for softmax training shape = (timesteps, features)
#------------------------------------------------------------------------------
OH_encoder = OneHotEncoder(sparse=False)
Y_train_OHE = OH_encoder.fit_transform(Y_train.reshape(Y_train.shape[0], -1))
df_Y_train_OHE = pd.DataFrame(Y_train_OHE)
df_X_train = pd.DataFrame(X_train.reshape(Y_train.shape[0], -1))
Y_train_OHE = np.reshape(Y_train_OHE, (Y_train.shape[0], Y_train.shape[1], -1))
if cnf.use_test_data == True: 
    Y_test_OHE = OH_encoder.transform(Y_test.reshape(Y_test.shape[0], -1))
    df_X_test = pd.DataFrame(X_test.reshape(Y_test.shape[0], -1))
    df_Y_test_OHE = pd.DataFrame(Y_test_OHE)
    Y_test_OHE = np.reshape(Y_test_OHE, (Y_test.shape[0], Y_test.shape[1], -1))

# [SAVE FILES]
#==============================================================================
# Save the trained preprocessing systems (normalizer and encoders) for further use 
#==============================================================================
print('''STEP 3 -----> Save files
''')

# save encoder
#------------------------------------------------------------------------------
if cnf.color_encoding == True:
    encoder_path = os.path.join(GlobVar.pp_path, 'categorical_encoder.pkl')
    with open(encoder_path, 'wb') as file:
        pickle.dump(categorical_encoder, file)

# save csv files
#------------------------------------------------------------------------------
file_loc = os.path.join(GlobVar.pp_path, 'CCM_preprocessed.xlsx')  
writer = pd.ExcelWriter(file_loc, engine='xlsxwriter')
df_X_train.to_excel(writer, sheet_name='train inputs', index=False)
df_Y_train_OHE.to_excel(writer, sheet_name='train labels', index=False)
if cnf.use_test_data == True:  
    df_X_test.to_excel(writer, sheet_name='test inputs', index=False)
    df_Y_test_OHE.to_excel(writer, sheet_name='test labels', index=False)

writer.close()

# [REPORT AND ANALYSIS]
#==============================================================================
# ....
#==============================================================================
if cnf.use_test_data == True:
    most_freq_train = trainset.value_counts().idxmax()
    most_freq_test = testset.value_counts().idxmax()
else:    
    most_freq_train = FAIRS_categorical.value_counts().idxmax()
    most_freq_test = 'None'

if cnf.color_encoding == True:
    encoding_desc = 'Data is encoded by roulette colors: Green as 0, Black as 1, Red as 2'    
else:
    encoding_desc = 'Data is encoded as observed numbers'

print(f'''
-------------------------------------------------------------------------------
{encoding_desc}
-------------------------------------------------------------------------------
Number of timepoints in train dataset: {train_samples}
Number of timepoints in test dataset:  {test_samples}
-------------------------------------------------------------------------------  
DISTRIBUTION OF CLASSES
-------------------------------------------------------------------------------  
Most frequent class in train dataset:  {most_freq_train}
Most frequent class in test dataset:   {most_freq_test}
Number of represented classes in train dataset: {trainset.nunique()}
Number of represented classes in test dataset: {testset.nunique()}
''')

# [DEFINE AND BUILD MODEL]
#==============================================================================
# module for the selection of different operations
#==============================================================================
print('''STEP 4 -----> Build the model and start training
''')
trainworker = ModelTraining(device=cnf.training_device, seed=cnf.seed, 
                            use_mixed_precision=cnf.use_mixed_precision) 
model_savepath = PP.model_savefolder(GlobVar.model_path, 'FAIRSCCM')

# initialize model class
#------------------------------------------------------------------------------
modelframe = ColorCodeModel(cnf.learning_rate, cnf.window_size, cnf.output_size, 
                            cnf.neuron_baseline, cnf.embedding_size, cnf.kernel_size,
                            len(categories[0]), seed=cnf.seed, XLA_state=cnf.XLA_acceleration)
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

# training loop and model saving at end
#------------------------------------------------------------------------------
print(f'''Start model training for {cnf.epochs} epochs and batch size of {cnf.batch_size}
       ''')
RTH_callback = RealTimeHistory(model_savepath, validation=cnf.use_test_data)
if cnf.use_test_data == True:
    validation_data = (X_test, Y_test_OHE)   
else:
    validation_data = None 

if cnf.use_tensorboard == True:
    log_path = os.path.join(model_savepath, 'tensorboard')
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_path, histogram_freq=1)
    callbacks = [RTH_callback, tensorboard_callback]    
else:    
    callbacks = [RTH_callback]

training = model.fit(x=X_train, y=Y_train_OHE, batch_size=cnf.batch_size, 
                     validation_data=validation_data, epochs = cnf.epochs, 
                     callbacks = callbacks, workers = 6, use_multiprocessing=True)

model.save(model_savepath)

# save model parameters in txt files
#------------------------------------------------------------------------------
parameters = {'Number of train samples' : train_samples,
              'Number of test samples' : test_samples,
              'Class encoding' : cnf.color_encoding,
              'Lowest neurons number' : cnf.neuron_baseline,
              'Window size' : cnf.window_size,
              'Output seq length' : cnf.output_size,
              'Embedding dimensions' : cnf.embedding_size,             
              'Batch size' : cnf.batch_size,
              'Learning rate' : cnf.learning_rate,
              'Epochs' : cnf.epochs}

trainworker.model_parameters(parameters, model_savepath)

# [MODEL VALIDATION]
#==============================================================================
# ...
#==============================================================================
print(f'''STEP 5 -----> Evaluate the model''')

validator = ModelValidation(model)

# predict lables from train set
#------------------------------------------------------------------------------
predicted_train = model.predict(X_train, verbose=0)
y_pred_labels = np.argmax(predicted_train, axis=-1)
y_true_labels = np.argmax(Y_train_OHE, axis=-1)
Y_pred, Y_true = y_pred_labels[:, 0], y_true_labels[:, 0]

# show predicted classes (train dataset)
#------------------------------------------------------------------------------
class_pred, class_true = np.unique(Y_pred), np.unique(Y_true)
print(f'''
Number of classes observed in train (true labels): {len(class_true)}
Number of classes observed in train (predicted labels): {len(class_pred)}
Classes observed in predicted train labels:''')
for x in class_pred:
    print(x)

# generate confusion matrix from train set (if class num is equal)
#------------------------------------------------------------------------------
try:
    validator.FAIRS_confusion(Y_true, Y_pred, 'train', model_savepath)
    #validator.FAIRS_ROC_curve(y_true_labels, y_pred_labels, categories_mapping, 'train', model_savepath, 400)
except Exception as e:
    print('Could not generate confusion matrix for train dataset')
    print('Error:', str(e))

# predict lables from test set
#------------------------------------------------------------------------------
if cnf.use_test_data == True:
    predicted_test = model.predict(X_test, verbose=0)
    y_pred_labels = np.argmax(predicted_test, axis=-1)
    y_true_labels = np.argmax(Y_test_OHE, axis=-1)
    Y_pred, Y_true = y_pred_labels[:, 0:1], y_true_labels[:, 0:1]

# show predicted classes (testdataset)
#------------------------------------------------------------------------------
    class_pred, class_true = np.unique(Y_pred), np.unique(Y_true)
    print(f'''
Number of classes observed in test (true labels): {len(class_true)}
Number of classes observed in test (predicted labels): {len(class_pred)}
Classes observed in predicted test labels:''')
    for x in class_pred:
        print(x)     

# generate confusion matrix from test set (if class num is equal)
#------------------------------------------------------------------------------
    try:
        validator.FAIRS_confusion(Y_true, Y_pred, 'test', model_savepath)
        #validator.FAIRS_ROC_curve(y_true_labels, y_pred_labels, categories_mapping, 'test', model_savepath, 400)
    except Exception as e:
        print('Could not generate confusion matrix for test dataset')
        print('Error:', str(e))



