import numpy as np

from FAIRS.commons.utils.preprocessing.mapping import RouletteMapper
from FAIRS.commons.utils.preprocessing.sequences import TimeSequencer
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger
    

# [CUSTOM DATA GENERATOR FOR TRAINING]
###############################################################################
# Generate and preprocess input and output for the machine learning model and build
# a tensor dataset with prefetching and batching
###############################################################################
class RouletteGenerator():

    def __init__(self, data):        
        
        self.data = data
        self.widows_size = CONFIG["dataset"]["WINDOW_SIZE"]         
        self.batch_size = CONFIG["training"]["BATCH_SIZE"] 
        self.sequencer = TimeSequencer() 
        self.mapper = RouletteMapper()       
        
    # ...
    #--------------------------------------------------------------------------
    def process_data(self):

        logger.info('Encoding position and colors from raw number timeseries') 
        roulette_dataset, color_encoder = self.mapper.encode_roulette_extractions(self.data)
        logger.info('Generate windows of historical extractions')
        train_data = self.sequencer.generate_historical_sequences(roulette_dataset)
        sequence, positions, colors = train_data[:, 0], train_data[:, 1], train_data[:, 2]             

        return sequence, positions, colors, color_encoder   
              
    








   


    