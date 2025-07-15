import torch
import keras
from keras import layers 

from FAIRS.app.src.constants import CONFIG, PAD_VALUE
from FAIRS.app.src.logger import logger
      

# [POSITIONAL EMBEDDING]
###############################################################################
@keras.saving.register_keras_serializable(package='CustomLayers', name='RouletteEmbedding')
class RouletteEmbedding(keras.layers.Layer):
    def __init__(self, embedding_dims, numbers, mask_padding=True, **kwargs):
        super(RouletteEmbedding, self).__init__(**kwargs)
        self.embedding_dims = embedding_dims
        self.numbers = numbers        
        self.mask_padding = mask_padding         
        # calculate radiand values for the different position of each number on
        # the roulette wheel, as they will be used for positional embeddings        
        self.numbers_embedding = layers.Embedding(
            input_dim=self.numbers, output_dim=self.embedding_dims, 
            mask_zero=mask_padding)
        
        self.embedding_scale = keras.ops.sqrt(self.embedding_dims)
       
    # implement positional embedding through call method  
    #--------------------------------------------------------------------------    
    def call(self, inputs):       
        # Get embeddings for the numbers
        embedded_numbers = self.numbers_embedding(inputs)  
        embedded_numbers *= self.embedding_scale        

        # Apply mask if 'mask_negative' is True
        if self.mask_padding:
            mask = self.compute_mask(inputs)
            mask = keras.ops.expand_dims(
                keras.ops.cast(mask, keras.config.floatx()), axis=-1)
            embedded_numbers *= mask

        return embedded_numbers
    
    # compute the mask for padded sequences  
    #--------------------------------------------------------------------------
    def compute_mask(self, inputs, mask=None):        
        mask = keras.ops.not_equal(inputs, PAD_VALUE)        
        
        return mask
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(RouletteEmbedding, self).get_config()
        config.update({'numbers': self.numbers,                       
                       'embedding_dims': self.embedding_dims,                       
                       'mask_padding': self.mask_padding})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)
    

