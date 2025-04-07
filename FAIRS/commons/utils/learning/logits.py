import keras
from keras import layers, activations
import torch

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

    
# [ADD NORM LAYER]
###############################################################################
@keras.saving.register_keras_serializable(package='CustomLayers', name='AddNorm')
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
@keras.saving.register_keras_serializable(package='CustomLayers', name='QScoreNet')
class QScoreNet(keras.layers.Layer):
    def __init__(self, dense_units, output_size, seed, **kwargs):
        super(QScoreNet, self).__init__(**kwargs)
        self.dense_units = dense_units
        self.output_size = output_size
        self.seed = seed
        # define Q score layers as Dense layers with linear activation
        self.Q1 = layers.Dense(self.dense_units, kernel_initializer='he_uniform')
        self.Q2 = layers.Dense(self.output_size, kernel_initializer='he_uniform', dtype=torch.float32)
        self.batch_norm = layers.BatchNormalization()         

    # build method for the custom layer 
    #--------------------------------------------------------------------------
    def build(self, input_shape):        
        super(QScoreNet, self).build(input_shape)           

    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------    
    def call(self, inputs, training=None):
        x = self.Q1(inputs)
        x = self.batch_norm(x, training=training) 
        x = activations.relu(x)      
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
    

###############################################################################
@keras.saving.register_keras_serializable(package='CustomLayers', name='BatchNormDense')
class BatchNormDense(layers.Layer):
    
    def __init__(self, units, **kwargs):
        super(BatchNormDense, self).__init__(**kwargs)
        self.units = units
        self.dense = layers.Dense(units, kernel_initializer='he_uniform') 
        self.batch_norm = layers.BatchNormalization()        

    #--------------------------------------------------------------------------
    def call(self, inputs, training=None):
        layer = self.dense(inputs)
        layer = layers.BatchNormalization()(layer)  
        layer = self.batch_norm(layer, training)
        layer = activations.relu(layer) 

        return layer

    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(BatchNormDense, self).get_config()
        config.update({'units': self.units})

        return config

    # deserialization method  
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)
    
###############################################################################
@keras.saving.register_keras_serializable(package='CustomLayers', name='InverseFrequency')   
class InverseFrequency(layers.Layer):

    def __init__(self, **kwargs):
        super(InverseFrequency, self).__init__(**kwargs)

    #--------------------------------------------------------------------------
    def compute_inverse_freq(self, sample):
        # sample: 1-D tensor of integers for a single batch element
        unique, idx, count = keras.ops.bincount(sample)
        # Compute inverse frequency for each unique element
        inv_counts = 1.0 / keras.ops.cast(count, torch.float32)
        # Map each element in the sample to its inverse frequency
        frequencies = keras.ops.take(inv_counts, idx, axis=-1)

        return frequencies

    #--------------------------------------------------------------------------
    def call(self, inputs, training=None):        
        inputs = keras.ops.cast(inputs, torch.int32)
        inverse_frequencies = keras.ops.map(self.compute_inverse_freq, inputs)

        return inverse_frequencies

    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(InverseFrequency, self).get_config()        
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)  

      

   