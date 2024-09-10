# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.preprocessing import PreProcessing
from FAIRS.commons.utils.learning.inferencer import Inference
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD DATA]
    #--------------------------------------------------------------------------
    # Load dataset of prediction inputs (if the file is present in the target folder)
    # else creates a new csv file named predictions_inputs.csv    
    filepath = os.path.join(DATA_PATH, 'FAIRS_dataset.csv')                 
    df_timeseries = pd.read_csv(filepath, sep= ';', encoding='utf-8')
    df_timeseries = df_timeseries[-cnf.PREDICTIONS_SIZE:]
    df_timeseries.reset_index(drop=True, inplace=True)

    # Load model    
    inference = Inference(cnf.SEED)
    model, parameters = inference.load_pretrained_model(CHECKPOINT_PATH)
    model_folder = inference.folder_path
    model.summary(expand_nested=True)

    # Load normalizer and encoders    
    pp_path = os.path.join(model_folder, 'preprocessing')
    if parameters['model_name'] == 'CCM':    
        encoder_path = os.path.join(pp_path, 'categorical_encoder.pkl')
        with open(encoder_path, 'rb') as file:
            encoder = pickle.load(file)    

    # 2. [PREPROCESS DATA FOR DIFFERENT MODEL]
    #--------------------------------------------------------------------------
    preprocessor = PreProcessing()

    # Preprocessd data according to each model pipeline    
    pp_path = os.path.join(model_folder, 'preprocessing')
    if parameters['model_name'] == 'CCM':
        # map numbers to roulette color, reshape array and generate window dataset        
        df_predictions = preprocessor.roulette_colormapping(df_timeseries, no_mapping=False)    
        categories = [['green', 'black', 'red']]
        timeseries = encoder.transform(df_predictions['encoding'].values.reshape(-1, 1))
        timeseries = pd.DataFrame(timeseries, columns=['encoding'])
        pred_inputs, _ = preprocessor.timeseries_labeling(timeseries, parameters['window_size'])
    else:
        df_predictions = preprocessor.roulette_positions(df_timeseries)
        df_predictions = preprocessor.roulette_colormapping(df_predictions, no_mapping=True)
        categories = [[x for x in df_predictions['encoding'].unique()]]
        timeseries = df_predictions[['encoding', 'position']]    
        val_inputs, _ = preprocessor.timeseries_labeling(timeseries['encoding'], parameters['window_size'])
        pos_inputs, _ = preprocessor.timeseries_labeling(timeseries['position'], parameters['window_size'])

    # 3. [PERFORM PREDICTIONS]
    #--------------------------------------------------------------------------
    # predict extractions using the pretrained ColorCode model, generate a dataframe
    # containing original values and predictions
    
    print('Perform prediction using the loaded model\n')
    if parameters['model_name'] == 'CCM':
        # create dummy arrays to fill first positions 
        nan_array_probs = np.full((parameters['window_size'], 3), np.nan)
        nan_array_values = np.full((parameters['window_size'], 1), np.nan)
        # create and reshape last window of inputs to obtain the future prediction
        last_window = timeseries['encoding'].tail(parameters['window_size'])
        last_window = np.reshape(last_window, (1, parameters['window_size'], 1))
        # predict from inputs and last window and stack arrays   
        probability_vectors = model.predict(pred_inputs)   
        next_prob_vector = model.predict(last_window)
        predicted_probs = np.vstack((nan_array_probs, probability_vectors, next_prob_vector))
        # find the most probable class using argmax on the probability vector
        expected_value = np.argmax(probability_vectors, axis=-1)    
        next_exp_value = np.argmax(next_prob_vector, axis=-1)
        # decode the classes to obtain original color code  
        expected_value = encoder.inverse_transform(expected_value.reshape(-1, 1))       
        next_exp_value = encoder.inverse_transform(next_exp_value.reshape(-1, 1))
        predicted_value = np.vstack((nan_array_values, expected_value, next_exp_value))    
        # create the dataframe by adding the new columns with predictions
        df_timeseries.loc[df_timeseries.shape[0]] = ['?', '?'] 
        df_timeseries['probability of green'] = predicted_probs[:, 0]
        df_timeseries['probability of black'] = predicted_probs[:, 1]
        df_timeseries['probability of red'] = predicted_probs[:, 2] 
        df_timeseries['predicted color'] = predicted_value[:, 0]      
        
    # predict extractions using the pretrained NumMatrix model, generate a dataframe
    # containing original values and predictions     
    else: 
        # create dummy arrays to fill first positions 
        nan_array_probs = np.full((parameters['window_size'], 37), np.nan)
        nan_array_values = np.full((parameters['window_size'], 1), np.nan)
        # create and reshape last window of inputs to obtain the future prediction
        last_window_ext = timeseries['encoding'].tail(parameters['window_size'])
        last_window_ext = np.reshape(last_window_ext, (1, parameters['window_size'], 1))
        last_window_pos = timeseries['position'].tail(parameters['window_size'])
        last_window_pos = np.reshape(last_window_pos, (1, parameters['window_size'], 1))
        # predict from inputs and last window    
        probability_vectors = model.predict([val_inputs, pos_inputs]) 
        next_prob_vector = model.predict([last_window_ext, last_window_pos])
        predicted_probs = np.vstack((nan_array_probs, probability_vectors, next_prob_vector))
        # find the most probable class using argmax on the probability vector
        expected_value = np.argmax(probability_vectors, axis=-1)    
        next_exp_value = np.argmax(next_prob_vector, axis=-1)     
        predicted_values = np.vstack((nan_array_values, expected_value.reshape(-1, 1), next_exp_value.reshape(-1, 1)))     
        # create the dataframe by adding the new columns with predictions
        df_timeseries.loc[df_timeseries.shape[0]] = ['?', '?', '?'] 
        for x in range(37):
            df_timeseries[f'probability of {x+1}'] = predicted_probs[:, x]     
        df_timeseries['predicted number'] = predicted_values[:, 0] 

    # print predictions on console
    
    print(f'Next predicted value: {next_exp_value[0,0]}\n')   
    print('Probability vector from softmax (%):')
    for i, x in enumerate(next_prob_vector[0]):
        if parameters['model_name'] == 'CCM':
            i = encoder.inverse_transform(np.reshape(i, (1, 1)))
            print(f'{i[0,0]} = {round((x * 100), 4)}')  
        else:
            print(f'{i+1} = {round((x * 100), 4)}')

    # save files as .csv in prediction folder    
    if parameters['model_name'] == 'CCM':  
        file_loc = os.path.join(PREDICTIONS_PATH, 'CCM_predictions.csv')         
        df_timeseries.to_csv(file_loc, index=False, sep=';', encoding='utf-8')
    else:
        file_loc = os.path.join(PREDICTIONS_PATH, 'NMM_predictions.csv')         
        df_timeseries.to_csv(file_loc, index=False, sep=';', encoding='utf-8')





