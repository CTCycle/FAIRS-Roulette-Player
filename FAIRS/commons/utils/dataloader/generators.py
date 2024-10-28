import numpy as np

from FAIRS.commons.utils.dataloader.serializer import get_training_dataset
from FAIRS.commons.utils.process.mapping import RouletteMapper
from FAIRS.commons.utils.process.sequences import TimeSequencer
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger
    

# [CUSTOM DATA GENERATOR FOR TRAINING]
###############################################################################
# Generate and preprocess input and output for the machine learning model and build
# a tensor dataset with prefetching and batching
###############################################################################
class RouletteGenerator():

    def __init__(self):        
        
        self.widows_size = CONFIG["dataset"]["PERCEPTIVE_SIZE"]         
        self.batch_size = CONFIG["training"]["BATCH_SIZE"] 
        self.sequencer = TimeSequencer() 
        self.mapper = RouletteMapper() 
        self.data = get_training_dataset()      
        
    # ...
    #--------------------------------------------------------------------------
    def prepare_roulette_dataset(self):

        logger.info('Encoding position and colors from raw number timeseries') 
        roulette_dataset, color_encoder = self.mapper.encode_roulette_extractions(self.data)
        roulette_dataset = roulette_dataset.drop(columns=['color'], axis=1)
        roulette_dataset = roulette_dataset.to_numpy()               

        return roulette_dataset, color_encoder   
              
    








   


    