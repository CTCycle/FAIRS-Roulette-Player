import numpy as np

from FAIRS.commons.utils.dataloader.serializer import get_extraction_dataset
from FAIRS.commons.utils.process.mapping import RouletteMapper
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger
    

# [CUSTOM DATA GENERATOR FOR TRAINING]
###############################################################################
# Generate and preprocess input and output for the machine learning model and build
# a tensor dataset with prefetching and batching
###############################################################################
class RouletteGenerator():

    def __init__(self, configuration):        
        
        self.widows_size = configuration["model"]["PERCEPTIVE_FIELD"]         
        self.batch_size = configuration["training"]["BATCH_SIZE"] 
        self.sample_size = configuration["dataset"]["SAMPLE_SIZE"]         
        self.mapper = RouletteMapper()               
        
    # ...
    #--------------------------------------------------------------------------
    def prepare_roulette_dataset(self, path):
        
        self.data = get_extraction_dataset(path, self.sample_size) 
        roulette_dataset, color_encoder = self.mapper.encode_roulette_extractions(self.data)
        roulette_dataset = roulette_dataset.drop(columns=['color'], axis=1)
        roulette_dataset = roulette_dataset.to_numpy(dtype=np.int32)               

        return roulette_dataset, color_encoder   
              
    








   


    