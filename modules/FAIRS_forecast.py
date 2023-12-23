import os
import sys
import numpy as np
import pandas as pd
import pickle

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
from modules.components.training_classes import ModelTraining
import modules.global_variables as GlobVar
import configurations as cnf

# [LOAD MODEL AND DATA]
#==============================================================================
# ....
#==============================================================================        
print(f'''
-------------------------------------------------------------------------------
FAIRS predictions
-------------------------------------------------------------------------------
Predict roulette extractions by loading a pretrained model and using previous
extracted numbers as input
''')

# Load dataset of prediction inputs (if the file is present in the target folder)
# else creates a new csv file named predictions_inputs.csv
#------------------------------------------------------------------------------
if 'predictions_input.csv' not in os.listdir(GlobVar.pred_path):
    filepath = os.path.join(GlobVar.data_path, 'FAIRS_dataset.csv')                
    df_predictions = pd.read_csv(filepath, sep= ';', encoding='utf-8')    
else:
    filepath = os.path.join(GlobVar.pred_path, 'predictions_inputs.csv')                
    df_predictions = pd.read_csv(filepath, sep= ';', encoding='utf-8')

df_predictions = df_predictions[-cnf.predictions_size:]
df_predictions.reset_index(inplace=True)

# Load model
#------------------------------------------------------------------------------
trainworker = ModelTraining(device = cnf.training_device) 
model = trainworker.load_pretrained_model(GlobVar.model_path)
load_path = trainworker.model_path
parameters = trainworker.model_configuration
model.summary(expand_nested=True)

# Load normalizer and encoders
#------------------------------------------------------------------------------
if parameters['Model name'] == 'CCM':    
    encoder_path = os.path.join(load_path, 'preprocessed data', 'categorical_encoder.pkl')
    with open(encoder_path, 'rb') as file:
        encoder = pickle.load(file)    

# [PREPROCESS DATA FOR DIFFERENT MODEL]
#==============================================================================
# ...
#==============================================================================
PP = PreProcessing()

# map numbers to roulette color, reshape array and generate window dataset
# CCM model
#------------------------------------------------------------------------------
if parameters['Model name'] == 'CCM':    
    df_predictions = PP.roulette_colormapping(df_predictions, no_mapping=False)
    timeseries = df_predictions['encoding']
    timeseries = timeseries.values.reshape(-1, 1)
    categories = [['green', 'black', 'red']]
    timeseries = encoder.transform(timeseries)
    timeseries = pd.DataFrame(timeseries, columns=['encoding'])
    predictions_inputs, _ = PP.timeseries_labeling(timeseries, parameters['Window size'], 
                                                         parameters['Output seq length'])
else:
    df_predictions = PP.roulette_positions(df_predictions)
    df_predictions = PP.roulette_colormapping(df_predictions, no_mapping=True)
    categories = [[x for x in df_predictions['encoding'].unique()]]
    timeseries = df_predictions[['encoding', 'position']]    
    val_inputs, _ = PP.timeseries_labeling(timeseries['encoding'], parameters['Window size'], 
                                            parameters['Output seq length'])
    pos_inputs, _ = PP.timeseries_labeling(timeseries['position'], parameters['Window size'], 
                                            parameters['Output seq length'])

# [PERFORM PREDICTIONS]
#==============================================================================
# ....
#==============================================================================
print('''Perform prediction using the loaded model
''')

# inverse encoding of the classes (CCM)
#------------------------------------------------------------------------------ 
if parameters['Model name'] == 'CCM': 
    last_window = timeseries['encoding'].to_list()[-parameters['Window size']:]
    last_window = np.reshape(last_window, (1, parameters['Window size'], 1))

    probability_vectors = model.predict(predictions_inputs)
    next_prob_vector = model.predict(last_window)

    expected_class = np.argmax(probability_vectors, axis=-1)    
    next_exp_class = np.argmax(next_prob_vector, axis=-1)
    original_class = np.array(timeseries['encoding'].to_list()).reshape(-1, 1) 

    expected_color = encoder.inverse_transform(expected_class)       
    next_exp_color = encoder.inverse_transform(next_exp_class)
    original_names = encoder.inverse_transform(original_class) 

    expected_color = expected_color.flatten().tolist() 
    next_exp_color = next_exp_color.flatten().tolist()[0]   
    original_names = np.append(original_names.flatten().tolist(), '?')
    sync_expected_vector = {'Green' : [], 'Black' : [], 'Red' : []}

# inverse encoding of the classes (CCM)
#------------------------------------------------------------------------------ 
else: 
    last_window_val = timeseries['encoding'].to_list()[-parameters['Window size']:]
    last_window_val = np.reshape(last_window_val, (1, parameters['Window size'], 1))
    last_window_pos = timeseries['position'].to_list()[-parameters['Window size']:]
    last_window_pos = np.reshape(last_window_val, (1, parameters['Window size'], 1))

    probability_vectors = model.predict([val_inputs, pos_inputs])
    next_prob_vector = model.predict([last_window_val, last_window_pos])

    expected_class = np.argmax(probability_vectors, axis=-1)    
    next_exp_class = np.argmax(next_prob_vector, axis=-1)
    original_class = np.array(timeseries['encoding'].to_list()).reshape(-1, 1)     

    expected_color = expected_class.flatten().tolist() 
    next_exp_color = next_exp_class.flatten().tolist()[0]   
    original_names = np.append(original_class.flatten().tolist(), '?')
    sync_expected_vector = {'Green' : [], 'Black' : [], 'Red' : []}         
    expected_color = expected_class.flatten().tolist() 
    next_exp_color = next_exp_class.flatten().tolist()[0]   
    original_names = np.append(original_class.flatten().tolist(), '?')
    sync_expected_vector = {f'{i}': [] for i in range(37)}

# synchronize the window of timesteps with the predictions (CCM)
#------------------------------------------------------------------------------ 
sync_expected_color = []
for ts in range(parameters['Window size']):
    if parameters['Model name'] == 'CCM':         
        sync_expected_vector['Green'].append('')
        sync_expected_vector['Black'].append('')
        sync_expected_vector['Red'].append('')
        sync_expected_color.append('')
    else:
        sync_expected_color.append('')
        for i in range(37):
            sync_expected_vector[f'{i}'].append('')           
                
for x, z in zip(probability_vectors, expected_color):
    if parameters['Model name'] == 'CCM':          
        sync_expected_vector['Green'].append(x[0,0])
        sync_expected_vector['Black'].append(x[0,1])
        sync_expected_vector['Red'].append(x[0,2])
        sync_expected_color.append(z)
    else:
        sync_expected_color.append(z)
        for i in range(37):
            sync_expected_vector[f'{i}'].append(x[0,i])            

for i in range(next_prob_vector.shape[1]):
    if parameters['Model name'] == 'CCM':          
        sync_expected_vector['Green'].append(next_prob_vector[0,i,0])
        sync_expected_vector['Black'].append(next_prob_vector[0,i,1])
        sync_expected_vector['Red'].append(next_prob_vector[0,i,2])
        sync_expected_color.append(next_exp_color)
    else:
        sync_expected_color.append(next_exp_color)
        for r in range(37):
            sync_expected_vector[f'{r}'].append(next_prob_vector[0,i,r])

# add column with prediction to dataset
#------------------------------------------------------------------------------
    timeseries.loc[len(timeseries.index)] = None
    timeseries['extraction'] = original_names
    timeseries['predicted extraction'] = sync_expected_color    
    df_probability = pd.DataFrame(sync_expected_vector)
    df_merged = pd.concat([timeseries, df_probability], axis=1)

# [PRINT PREDICTIONS]
#==============================================================================
# Save the trained preprocessing systems (normalizer and encoders) for further use 
#==============================================================================
print(f'''
-------------------------------------------------------------------------------
Next predicted color: {next_exp_color}
-------------------------------------------------------------------------------
''')
print('Probability vector from softmax (%):')
for i, (x, y) in enumerate(sync_expected_vector.items()):
    print(f'{x} = {round((next_prob_vector[0,0,i] * 100), 4)}')


# [SAVE FILES]
#==============================================================================
# Save the trained preprocessing systems (normalizer and encoders) for further use 
#==============================================================================
print('''
-------------------------------------------------------------------------------
Saving predictions file (as CSV)
-------------------------------------------------------------------------------
''')
if parameters['Model name'] == 'CCM':  
    file_loc = os.path.join(GlobVar.pred_path, 'CCM_predictions.csv')         
    df_merged.to_csv(file_loc, index=False, sep = ';', encoding = 'utf-8')
else:
    file_loc = os.path.join(GlobVar.pred_path, 'NMM_predictions.csv')         
    df_merged.to_csv(file_loc, index=False, sep = ';', encoding = 'utf-8')





