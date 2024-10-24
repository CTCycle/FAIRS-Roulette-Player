import numpy as np
import torch
import keras
import tensorflow as tf
from keras import activations, layers 

from FAIRS.commons.constants import CONFIG, NUMBERS
from FAIRS.commons.logger import logger
      

# [POSITIONAL EMBEDDING]
###############################################################################
@keras.utils.register_keras_serializable(package='CustomLayers', name='PositionalEmbedding')
class PositionalEmbedding(keras.layers.Layer):
    def __init__(self, embedding_dims, sequence_length, mask_zero=True, **kwargs):
        super(PositionalEmbedding, self).__init__(**kwargs)
        self.embedding_dims = embedding_dims
        self.sequence_length = sequence_length         
        self.mask_zero = mask_zero
        
        # calculate radiand values for the different position of each number on
        # the roulette wheel, as they will be used for positional embeddings
        self.radiant_gap = (2 * np.pi)/NUMBERS
        self.numbers_embedding = layers.Embedding(input_dim=self.sequence_length, 
                                                  output_dim=self.embedding_dims, 
                                                  mask_zero=mask_zero)
        self.position_embeddings = layers.Embedding(input_dim=self.sequence_length, 
                                                    output_dim=self.embedding_dims)
        self.embedding_scale = keras.ops.sqrt(keras.ops.cast(self.embedding_dims, torch.float32))       
    
    # implement positional embedding through call method  
    #--------------------------------------------------------------------------    
    def call(self, numbers, positions):        
        embedded_timeseries = self.numbers_embedding(numbers) 
        embedded_timeseries *= self.embedding_scale 
        # multiply each position with the radiant gap to obtain the radial position
        embedded_positions = positions * self.radiant_gap
        embedded_positions = self.position_embeddings(embedded_positions)     
        full_embedding = embedded_timeseries + embedded_positions
        
        if self.mask_zero:
            mask = keras.ops.not_equal(numbers, -1)
            mask = keras.ops.expand_dims(keras.ops.cast(mask, torch.float32), axis=-1)
            full_embedding *= mask

        return full_embedding
    
    # compute the mask for padded sequences  
    #--------------------------------------------------------------------------
    def compute_mask(self, inputs, mask=None):        
        mask = keras.ops.not_equal(inputs, -1)        
        
        return mask
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(PositionalEmbedding, self).get_config()
        config.update({'sequence_length': self.sequence_length,                       
                       'embedding_dims': self.embedding_dims,                       
                       'mask_zero': self.mask_zero})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)
    

