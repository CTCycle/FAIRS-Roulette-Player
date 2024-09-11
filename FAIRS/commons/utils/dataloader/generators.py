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

        sequence, positions, colors = data[:-1, 0], data[:-1, 1], data[:-1, 2]                
        sequence_out, position_out, color_out = data[1:, 0], data[1:, 1], data[1:, 2]           

        return (sequence, positions, sequence, position_out), position_out   
   
              
    # effectively build the tf.dataset and apply preprocessing, batching and prefetching
    #--------------------------------------------------------------------------
    def build_tensor_dataset(self, data : np.array, buffer_size=tf.data.AUTOTUNE):

        num_samples = data.shape[0]         
        dataset = tf.data.Dataset.from_tensor_slices(data)
        dataset = dataset.shuffle(buffer_size=num_samples)          
        dataset = dataset.map(self.process_data, num_parallel_calls=buffer_size)                
        dataset = dataset.batch(self.batch_size)
        dataset = dataset.prefetch(buffer_size=buffer_size)

        return dataset
        

# wrapper function to run the data pipeline from raw inputs to tensor dataset
###############################################################################
def training_data_pipeline(train_data, validation_X):    
        
        generator = DataGenerator() 
        train_dataset = generator.build_tensor_dataset(train_data)
        validation_dataset = generator.build_tensor_dataset(validation_X)        
        for (x1, x2, x3, x4), y1 in train_dataset.take(1):
            logger.debug(f'X batch shape is: {x1.shape}')  
            logger.debug(f'Y batch shape is: {y1.shape}') 

        return train_dataset, validation_dataset






   


    