import numpy as np
import keras

from FAIRS.commons.utils.process.mapping import RouletteMapper
from FAIRS.commons.constants import CONFIG, PRED_PATH
from FAIRS.commons.logger import logger


###############################################################################
class RoulettePlayer:

    def __init__(self, model : keras.Model, configuration):        

        keras.utils.set_random_seed(configuration["SEED"])  
        self.mapper = RouletteMapper()              
        self.model = model 
        self.configuration = configuration        
        self.perceptive_field = configuration["model"]["PERCEPTIVE_FIELD"] 

        self.action_descriptions = {i: f"Bet on number {i}" for i in range(37)}
        self.action_descriptions[37] = "Bet on red"
        self.action_descriptions[38] = "Bet on black"
        self.action_descriptions[39] = "stop playing"
    

    #--------------------------------------------------------------------------    
    def get_perceptive_fields(self, data : np.array, fraction=1.0):

        extractions = data[:, 0]

        # Initialize the perceptive field filled with -1
        perceptive_field = np.full(shape=self.perceptive_field, fill_value=-1, dtype=np.int32)
        perceptive_fields_collection = [perceptive_field]

        # Generate rolling windows over the entire dataset
        for r in range(data.shape[0]):
            current_extraction = extractions[r]
            perceptive_field = np.delete(perceptive_field, 0)
            perceptive_field = np.append(perceptive_field, current_extraction)
            perceptive_fields_collection.append(perceptive_field)

        # Slice the collection to get only the desired fraction from the tail
        total_windows = len(perceptive_fields_collection)
        tail_length = int(fraction * total_windows)
        perceptive_fields_collection = perceptive_fields_collection[-tail_length:]

        return perceptive_fields_collection   
        
    #--------------------------------------------------------------------------    
    def play_roulette_game(self, data : np.array, fraction=1.0):

        perceptive_fields = self.get_perceptive_fields(data, fraction)
        predicted_actions, action_descriptions = [], []        

        for pf in perceptive_fields:
            pf = np.reshape(pf, newshape=(1, self.perceptive_field))
            action_logits = self.model.predict(pf, verbose=1)
            next_action = np.argmax(action_logits, axis=1)[0]
            action_description = self.action_descriptions[next_action] 
            predicted_actions.append(next_action) 
            action_descriptions.append(action_description)       

        # The number of predictions corresponds only to the tail of the data
        total_rows = data.shape[0]
        predicted_count = len(perceptive_fields)
        missing_count = total_rows - predicted_count

        # Create arrays with placeholders for all rows
        # Use np.nan for numeric predictions and empty strings for action descriptions
        predicted_extractions_full = np.full((total_rows, 1), np.nan, dtype=float)
        action_descriptions_full = np.full((total_rows, 1), '', dtype=object)

        # Fill in the tail rows with actual predictions
        predicted_extractions_full[missing_count:] = np.array(predicted_actions).reshape(-1, 1)
        action_descriptions_full[missing_count:] = np.array(action_descriptions).reshape(-1, 1)

        # Now stack them horizontally
        # Note: This will create an array of dtype=object since we're mixing strings and numbers.
        # If that's an issue, consider storing the entire result in a structured format or separate arrays.
        data = np.hstack((data, predicted_extractions_full, action_descriptions_full))

        return data           
            
        

        



