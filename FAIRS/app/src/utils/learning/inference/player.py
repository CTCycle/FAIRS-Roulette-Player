import os
import pandas as pd
import numpy as np
import keras

from FAIRS.app.src.utils.data.process.mapping import RouletteMapper
from FAIRS.app.src.constants import CONFIG, INFERENCE_PATH
from FAIRS.app.src.logger import logger


###############################################################################
def save_predictions_to_csv(predictions : np.array, model_name):

    columns = ['extraction', 'position', 'color', 'expected_action', 'action_description']
    predictions_path = os.path.join(PRED_PATH, f'{model_name}_predictions.csv')
    predictions = pd.DataFrame(predictions, columns=columns)   
    predictions.to_csv(predictions_path, index=False)



###############################################################################
class RoulettePlayer:

    def __init__(self, model : keras.Model, configuration):        

        keras.utils.set_random_seed(configuration["SEED"])  
        self.mapper = RouletteMapper()   

        self.model = model 
        self.configuration = configuration        
        self.perceptive_size = configuration["model"]["PERCEPTIVE_FIELD"] 
        self.data_fraction = CONFIG['inference']['DATA_FRACTION']

        self.action_descriptions = {i: f"Bet on number {i}" for i in range(37)}
        self.action_descriptions[37] = "Bet on red"
        self.action_descriptions[38] = "Bet on black"
        self.action_descriptions[39] = "stop playing"

        self.last_states = None

    #--------------------------------------------------------------------------    
    def get_perceptive_fields(self, data : np.array, fraction=1.0):

        perceptive_field = np.full(shape=self.perceptive_size, fill_value=-1, dtype=np.int32)
        perceptive_fields = [perceptive_field]

        if data.shape[0] > 0:            
            extractions = data[:, 0] 
            # Generate rolling windows over the entire dataset
            for r in range(data.shape[0]):
                current_extraction = extractions[r]
                perceptive_field = np.delete(perceptive_field, 0)
                perceptive_field = np.append(perceptive_field, current_extraction)
                perceptive_fields.append(perceptive_field)            

            # Slice the collection to get only the desired fraction from the tail
            total_windows = len(perceptive_fields)
            tail_length = int(fraction * total_windows)
            perceptive_fields_collection = perceptive_fields[-tail_length:] 

            self.last_states = perceptive_fields[-1]       
        
        return perceptive_fields_collection   
        
    #--------------------------------------------------------------------------    
    def play_past_roulette_games(self, data : np.array):

        perceptive_fields = self.get_perceptive_fields(data, self.data_fraction)
        predicted_actions, action_descriptions = [], []        

        for pf in perceptive_fields:
            pf = np.reshape(pf, newshape=(1, self.perceptive_size))
            action_logits = self.model.predict(pf, verbose=1)
            next_action = np.argmax(action_logits, axis=1)[0]
            action_description = self.action_descriptions[next_action] 
            predicted_actions.append(next_action) 
            action_descriptions.append(action_description)       

        # count expected missing value as 0 if no series is provided, or as the 
        # the total length minus the perceptive field size otherwise
        missing_count = data.shape[0] - len(perceptive_fields) if data.shape[0] > 0 else 0       

        # Create arrays with placeholders for all rows and add np.nan for numeric predictions 
        # and empty strings for action descriptions
        predicted_extractions_full = np.full((data.shape[0], 1), np.nan, dtype=float)
        action_descriptions_full = np.full((data.shape[0], 1), '', dtype=object)

        # Fill in the tail rows with actual predictions
        predicted_extractions_full[missing_count:] = np.array(predicted_actions).reshape(-1, 1)
        action_descriptions_full[missing_count:] = np.array(action_descriptions).reshape(-1, 1)
        
        data = np.hstack((data, predicted_extractions_full, action_descriptions_full))

        return data 

    #--------------------------------------------------------------------------    
    def play_real_time_roulette(self):

        # Initialize the state if no predictions have been run till now        
        if self.last_states is None:
            self.last_states = np.full(shape=self.perceptive_size, fill_value=-1, dtype=np.int32)

        while True:
            current_state = np.reshape(self.last_states, newshape=(1, self.perceptive_size))           
            action_logits = self.model.predict(current_state, verbose=1)
            next_action = np.argmax(action_logits, axis=1)[0]
            action_description = self.action_descriptions[next_action]
            
            logger.info(f'FAIRSnet suggests to {action_description} (state: {next_action}) ')

            # Ask the user for the real roulette outcome
            user_input = input('Please enter the actual number (0-36) or type "exit" to interrupt: ').strip().lower()
            
            if user_input == 'exit':
                print("Exiting real-time play.")
                break

            # Validate that the input is a number
            if not user_input.isdigit():
                print('Please enter a number between 0 and 36.')
                continue

            real_number = int(user_input)
            if real_number < 0 or real_number > 36:
                print('Please enter a number between 0 and 36.')
                continue

            # Update the state array by removing the oldest number and appending the new one
            self.last_states = np.delete(self.last_states, 0)
            self.last_states = np.append(self.last_states, real_number)

           
                
            

            



