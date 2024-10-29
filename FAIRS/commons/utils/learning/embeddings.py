import numpy as np
import torch
import keras
from keras import activations, layers 

from FAIRS.commons.constants import CONFIG, NUMBERS
from FAIRS.commons.logger import logger
      

# [POSITIONAL EMBEDDING]
###############################################################################
@keras.utils.register_keras_serializable(package='CustomLayers', name='RouletteEmbedding')
class RouletteEmbedding(keras.layers.Layer):
    def __init__(self, embedding_dims, sequence_length, mask_negative=True, **kwargs):
        super(RouletteEmbedding, self).__init__(**kwargs)
        self.embedding_dims = embedding_dims
        self.sequence_length = sequence_length         
        self.mask_negative = mask_negative        
        
        # calculate radiand values for the different position of each number on
        # the roulette wheel, as they will be used for positional embeddings
        self.radiant_gap = (2 * np.pi)/NUMBERS
        self.numbers_embedding = layers.Embedding(input_dim=self.sequence_length, 
                                                  output_dim=self.embedding_dims, 
                                                  mask_zero=mask_negative)
        
        self.embedding_scale = keras.ops.sqrt(keras.ops.cast(self.embedding_dims, torch.float32)) 
       
    # implement positional embedding through call method  
    #--------------------------------------------------------------------------    
    def call(self, inputs):          
        
        # Get embeddings for the numbers
        embedded_numbers = self.numbers_embedding(inputs)  
        embedded_numbers *= self.embedding_scale        

        # Apply mask if 'mask_negative' is True
        if self.mask_negative:
            mask = keras.ops.not_equal(inputs, -1)
            mask = keras.ops.expand_dims(keras.ops.cast(mask, torch.float32), axis=-1)
            embedded_numbers *= mask

        return embedded_numbers
    
    # compute the mask for padded sequences  
    #--------------------------------------------------------------------------
    def compute_mask(self, inputs, mask=None):        
        mask = keras.ops.not_equal(inputs, -1)        
        
        return mask
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(RouletteEmbedding, self).get_config()
        config.update({'sequence_length': self.sequence_length,                       
                       'embedding_dims': self.embedding_dims,                       
                       'mask_negative': self.mask_negative})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)
    

