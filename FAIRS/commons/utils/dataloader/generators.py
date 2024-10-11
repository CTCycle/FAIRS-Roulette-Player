import numpy as np
import tensorflow as tf

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger
    

# [CUSTOM DATA GENERATOR FOR TRAINING]
###############################################################################
# Generate and preprocess input and output for the machine learning model and build
# a tensor dataset with prefetching and batching
###############################################################################
class DataGenerator():

    def __init__(self):        
        
        self.widows_size = CONFIG["dataset"]["WINDOW_SIZE"]         
        self.batch_size = CONFIG["training"]["BATCH_SIZE"]  
    
    # ...
    #--------------------------------------------------------------------------
    def process_data(self, data): 

        sequence, positions, colors = data[:, :, 0], data[:, :, 1], data[:, :, 2]             

        return sequence, positions, colors   
              
    # effectively build the tf.dataset and apply preprocessing, batching and prefetching
    #--------------------------------------------------------------------------
    def build_tensor_dataset(self, data : np.array, buffer_size=tf.data.AUTOTUNE):

              
        dataset = tf.data.Dataset.from_tensor_slices(data)
        dataset = dataset.map(self.process_data, num_parallel_calls=buffer_size)                
        dataset = dataset.batch(self.batch_size)
        dataset = dataset.prefetch(buffer_size=buffer_size)

        return dataset
        

# wrapper function to run the data pipeline from raw inputs to tensor dataset
###############################################################################
def training_data_pipeline(train_data, validation_data):    
        
        generator = DataGenerator() 
        train_dataset = generator.build_tensor_dataset(train_data)
        validation_dataset = generator.build_tensor_dataset(validation_data)        
        for x, _, _ in train_dataset.take(1):
            logger.debug(f'X batch shape is: {x.shape}')             

        return train_dataset, validation_dataset






   


    