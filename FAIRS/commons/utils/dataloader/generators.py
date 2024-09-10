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
    def process_data(self, X, Y): 

        sequence = X[:, 0]
        positions = X[:, 1]         
        output_seq = Y[:, 0]
        output_color = Y[:, 2]      

        return (sequence, positions), (output_seq, output_color)   

   
              
    # effectively build the tf.dataset and apply preprocessing, batching and prefetching
    #--------------------------------------------------------------------------
    def build_tensor_dataset(self, inputs : np.array, outputs : np.array, 
                             buffer_size=tf.data.AUTOTUNE):

        num_samples = inputs.shape[0]         
        dataset = tf.data.Dataset.from_tensor_slices((inputs, outputs))
        dataset = dataset.shuffle(buffer_size=num_samples)          
        dataset = dataset.map(self.process_data, num_parallel_calls=buffer_size)                
        dataset = dataset.batch(self.batch_size)
        dataset = dataset.prefetch(buffer_size=buffer_size)

        return dataset
        

# wrapper function to run the data pipeline from raw inputs to tensor dataset
###############################################################################
def training_data_pipeline(train_X, train_Y, validation_X, validation_Y):    
        
        generator = DataGenerator()           

        train_dataset = generator.build_tensor_dataset(train_X, train_Y)
        validation_dataset = generator.build_tensor_dataset(validation_X, validation_Y)        
        for (x1, x2), (y1, y2) in train_dataset.take(1):
            logger.debug(f'X batch shape is: {x1.shape}')  
            logger.debug(f'Y batch shape is: {y1.shape}') 

        return train_dataset, validation_dataset






   


    