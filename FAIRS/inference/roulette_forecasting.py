# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.preprocessing.mapping import RouletteMapper
from FAIRS.commons.utils.preprocessing.sequences import TimeSequencer
from FAIRS.commons.utils.dataloader.serializer import get_predictions_dataset, ModelSerializer
from FAIRS.commons.utils.learning.inferencer import RouletteGenerator
from FAIRS.commons.constants import CONFIG, PRED_PATH
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD DATA]
    #--------------------------------------------------------------------------     
    # load data from csv, add paths to images 
    logger.info(f'Loading predictions dataset from {PRED_PATH}')    
    predictions_data = get_predictions_dataset()    

    # 2. [MAP DATA TO ROULETTE POSITIONS AND COLORS]
    #--------------------------------------------------------------------------    
    mapper = RouletteMapper()
    logger.info('Encoding position and colors from raw number timeseries')    
    predictions_data, color_encoder = mapper.encode_roulette_extractions(predictions_data)
    
    # 3. [GENERATE ROLLING SEQUENCES]
    #--------------------------------------------------------------------------
    sequencer = TimeSequencer() 
    shifted_sequences = sequencer.generate_shifted_sequences(predictions_data)    
      
    # 4. [LOAD MODEL]
    #--------------------------------------------------------------------------  
    # selected and load the pretrained model, then print the summary 
    modelserializer = ModelSerializer()         
    model, configuration, history = modelserializer.load_pretrained_model()
    model_folder = modelserializer.loaded_model_folder
    model.summary(expand_nested=True)      
 
    # 5. [GENERATE REPORTS]
    #--------------------------------------------------------------------------    
    generator = RouletteGenerator(model, configuration, shifted_sequences) 
    logger.info('Generating roulette series from last window')   
    generated_timeseries = generator.greed_search_generator()

    

    # 3. [PERFORM PREDICTIONS]
    #--------------------------------------------------------------------------
    # predict extractions using the pretrained ColorCode model, generate a dataframe
    # containing original values and predictions
    
    print('Perform prediction using the loaded model\n')
    # if parameters['model_name'] == 'CCM':
    #     # create dummy arrays to fill first positions 
    #     nan_array_probs = np.full((parameters['window_size'], 3), np.nan)
    #     nan_array_values = np.full((parameters['window_size'], 1), np.nan)
    #     # create and reshape last window of inputs to obtain the future prediction
    #     last_window = timeseries['encoding'].tail(parameters['window_size'])
    #     last_window = np.reshape(last_window, (1, parameters['window_size'], 1))
    #     # predict from inputs and last window and stack arrays   
    #     probability_vectors = model.predict(pred_inputs)   
    #     next_prob_vector = model.predict(last_window)
    #     predicted_probs = np.vstack((nan_array_probs, probability_vectors, next_prob_vector))
    #     # find the most probable class using argmax on the probability vector
    #     expected_value = np.argmax(probability_vectors, axis=-1)    
    #     next_exp_value = np.argmax(next_prob_vector, axis=-1)
    #     # decode the classes to obtain original color code  
    #     expected_value = encoder.inverse_transform(expected_value.reshape(-1, 1))       
    #     next_exp_value = encoder.inverse_transform(next_exp_value.reshape(-1, 1))
    #     predicted_value = np.vstack((nan_array_values, expected_value, next_exp_value))    
    #     # create the dataframe by adding the new columns with predictions
    #     df_timeseries.loc[df_timeseries.shape[0]] = ['?', '?'] 
    #     df_timeseries['probability of green'] = predicted_probs[:, 0]
    #     df_timeseries['probability of black'] = predicted_probs[:, 1]
    #     df_timeseries['probability of red'] = predicted_probs[:, 2] 
    #     df_timeseries['predicted color'] = predicted_value[:, 0]      
        
    # # predict extractions using the pretrained NumMatrix model, generate a dataframe
    # # containing original values and predictions     
    # else: 
    #     # create dummy arrays to fill first positions 
    #     nan_array_probs = np.full((parameters['window_size'], 37), np.nan)
    #     nan_array_values = np.full((parameters['window_size'], 1), np.nan)
    #     # create and reshape last window of inputs to obtain the future prediction
    #     last_window_ext = timeseries['encoding'].tail(parameters['window_size'])
    #     last_window_ext = np.reshape(last_window_ext, (1, parameters['window_size'], 1))
    #     last_window_pos = timeseries['position'].tail(parameters['window_size'])
    #     last_window_pos = np.reshape(last_window_pos, (1, parameters['window_size'], 1))
    #     # predict from inputs and last window    
    #     probability_vectors = model.predict([val_inputs, pos_inputs]) 
    #     next_prob_vector = model.predict([last_window_ext, last_window_pos])
    #     predicted_probs = np.vstack((nan_array_probs, probability_vectors, next_prob_vector))
    #     # find the most probable class using argmax on the probability vector
    #     expected_value = np.argmax(probability_vectors, axis=-1)    
    #     next_exp_value = np.argmax(next_prob_vector, axis=-1)     
    #     predicted_values = np.vstack((nan_array_values, expected_value.reshape(-1, 1), next_exp_value.reshape(-1, 1)))     
    #     # create the dataframe by adding the new columns with predictions
    #     df_timeseries.loc[df_timeseries.shape[0]] = ['?', '?', '?'] 
    #     for x in range(37):
    #         df_timeseries[f'probability of {x+1}'] = predicted_probs[:, x]     
    #     df_timeseries['predicted number'] = predicted_values[:, 0] 

    # # print predictions on console
    
    # print(f'Next predicted value: {next_exp_value[0,0]}\n')   
    # print('Probability vector from softmax (%):')
    # for i, x in enumerate(next_prob_vector[0]):
    #     if parameters['model_name'] == 'CCM':
    #         i = encoder.inverse_transform(np.reshape(i, (1, 1)))
    #         print(f'{i[0,0]} = {round((x * 100), 4)}')  
    #     else:
    #         print(f'{i+1} = {round((x * 100), 4)}')

    # # save files as .csv in prediction folder    
    # if parameters['model_name'] == 'CCM':  
    #     file_loc = os.path.join(PREDICTIONS_PATH, 'CCM_predictions.csv')         
    #     df_timeseries.to_csv(file_loc, index=False, sep=';', encoding='utf-8')
    # else:
    #     file_loc = os.path.join(PREDICTIONS_PATH, 'NMM_predictions.csv')         
    #     df_timeseries.to_csv(file_loc, index=False, sep=';', encoding='utf-8')





