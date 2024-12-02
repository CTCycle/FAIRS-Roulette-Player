import keras
from keras import activations, layers
import torch

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

    
# [ADD NORM LAYER]
###############################################################################
@keras.utils.register_keras_serializable(package='CustomLayers', name='AddNorm')
class AddNorm(keras.layers.Layer):
    def __init__(self, epsilon=10e-5, **kwargs):
        super(AddNorm, self).__init__(**kwargs)
        self.epsilon = epsilon
        self.add = layers.Add()
        self.layernorm = layers.LayerNormalization(epsilon=self.epsilon)    

    # build method for the custom layer 
    #--------------------------------------------------------------------------
    def build(self, input_shape):        
        super(AddNorm, self).build(input_shape)

    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------        
    def call(self, inputs):
        x1, x2 = inputs
        x_add = self.add([x1, x2])
        x_norm = self.layernorm(x_add)

        return x_norm
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(AddNorm, self).get_config()
        config.update({'epsilon' : self.epsilon})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)
    
    
# [CLASSIFIER]
###############################################################################
@keras.utils.register_keras_serializable(package='CustomLayers', name='QScoreNet')
class QScoreNet(keras.layers.Layer):
    def __init__(self, dense_units, output_size, seed, **kwargs):
        super(QScoreNet, self).__init__(**kwargs)
        self.dense_units = dense_units
        self.output_size = output_size
        self.seed = seed
        # apply the Q-score layers
        self.Q1 = layers.Dense(self.dense_units, kernel_initializer='he_uniform')
        self.Q2 = layers.Dense(self.output_size, kernel_initializer='he_uniform', dtype=torch.float32)
        self.batch_norm = layers.BatchNormalization()    
        self.dropout = layers.Dropout(rate=0.2, seed=seed)

    # build method for the custom layer 
    #--------------------------------------------------------------------------
    def build(self, input_shape):        
        super(QScoreNet, self).build(input_shape)           

    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------    
    def call(self, inputs, training=None):
        x = self.Q1(inputs)
        x = self.batch_norm(x, training=training)
        x = activations.elu(x)        
        x = self.dropout(x, training=training)
        output = self.Q2(x)                  

        return output
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(QScoreNet, self).get_config()
        config.update({'dense_units' : self.dense_units,
                       'output_size' : self.output_size,
                       'seed' : self.seed})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)
    

