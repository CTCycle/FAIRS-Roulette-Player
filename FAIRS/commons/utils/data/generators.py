import numpy as np

from FAIRS.commons.utils.data.serializer import DataSerializer
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
        self.serializer = DataSerializer(configuration)       
        self.mapper = RouletteMapper()   
        self.color_encoder = None        

    #--------------------------------------------------------------------------
    def process_roulette_dataset(self):        
        self.data = self.serializer.load_roulette_dataset(self.sample_size) 
        roulette_dataset, self.color_encoder = self.mapper.encode_roulette_extractions(self.data)
        roulette_dataset = roulette_dataset.drop(columns=['color'], axis=1)
        roulette_dataset = roulette_dataset.to_numpy(dtype=np.int32)               

        return roulette_dataset  
    
    #--------------------------------------------------------------------------
    def process_roulette_dataset(self):        
        self.data = self.serializer.load_roulette_dataset(self.sample_size) 
        roulette_dataset, self.color_encoder = self.mapper.encode_roulette_extractions(self.data)
        roulette_dataset = roulette_dataset.drop(columns=['color'], axis=1)
        roulette_dataset = roulette_dataset.to_numpy(dtype=np.int32)               

        return roulette_dataset
              
    








   


    