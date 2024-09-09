import os
import keras
from keras import activations, layers
import torch



from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

    
# [CLASSIFIER]
###############################################################################
@keras.utils.register_keras_serializable(package='CustomLayers', name='NumberPredictor')
class NumberPredictor(keras.layers.Layer):
    def __init__(self, dense_units, output_size, **kwargs):
        super(NumberPredictor, self).__init__(**kwargs)
        self.dense_units = dense_units
        self.output_size = output_size
        self.dense1 = layers.Dense(dense_units, activation='relu', 
                                   kernel_initializer='he_uniform')
        self.dense2 = layers.Dense(output_size, activation='softmax', 
                                   kernel_initializer='he_uniform', dtype=torch.float32)

    # build method for the custom layer 
    #--------------------------------------------------------------------------
    def build(self, input_shape):        
        super(NumberPredictor, self).build(input_shape)     
        

    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------    
    def call(self, x, training=None):
        x = self.dense1(x)
        output = self.dense2(x)          

        return output
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(NumberPredictor, self).get_config()
        config.update({'dense_units' : self.dense_units,
                       'output_size' : self.output_size})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)
    

# [CLASSIFIER]
###############################################################################
@keras.utils.register_keras_serializable(package='CustomLayers', name='ColorPredictor')
class ColorPredictor(keras.layers.Layer):
    def __init__(self, dense_units, output_size, **kwargs):
        super(ColorPredictor, self).__init__(**kwargs)
        self.dense_units = dense_units
        self.output_size = output_size
        self.dense1 = layers.Dense(dense_units, activation='relu', 
                                   kernel_initializer='he_uniform')
        self.dense2 = layers.Dense(output_size, activation='softmax', 
                                   kernel_initializer='he_uniform', dtype=torch.float32)

    # build method for the custom layer 
    #--------------------------------------------------------------------------
    def build(self, input_shape):        
        super(ColorPredictor, self).build(input_shape)     
        

    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------    
    def call(self, x, training=None):
        x = self.dense1(x)
        output = self.dense2(x)          

        return output
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(ColorPredictor, self).get_config()
        config.update({'dense_units' : self.dense_units,
                       'output_size' : self.output_size})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)