import os
import keras
from keras import activations, layers
import torch

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

    
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
        self.Q2 = layers.Dense(int(self.dense_units//2), kernel_initializer='he_uniform')
        self.Q3 = layers.Dense(int(self.dense_units//4), kernel_initializer='he_uniform')
        self.Q4 = layers.Dense(self.output_size, kernel_initializer='he_uniform', dtype=torch.float32)
        self.batch_norm1 = layers.BatchNormalization()
        self.batch_norm2 = layers.BatchNormalization()
        self.batch_norm3 = layers.BatchNormalization()
        self.dropout = layers.Dropout(rate=0.2, seed=seed)

    # build method for the custom layer 
    #--------------------------------------------------------------------------
    def build(self, input_shape):        
        super(QScoreNet, self).build(input_shape)           

    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------    
    def call(self, x, training=None):
        x = self.Q1(x)
        x = self.batch_norm1(x, training=training)
        x = activations.relu(x)
        x = self.Q2(x)
        x = self.batch_norm2(x, training=training)
        x = activations.relu(x)
        x = self.Q3(x)
        x = self.batch_norm3(x, training=training)
        x = activations.relu(x)
        x = self.dropout(x, training=training)
        output = self.Q4(x)                  

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