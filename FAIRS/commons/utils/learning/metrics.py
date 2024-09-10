import torch
import keras
import tensorflow as tf

from FAIRS.commons.constants import CONFIG, STATES, COLORS
from FAIRS.commons.logger import logger

# [LOSS FUNCTION]
###############################################################################
class ScaledCategoricalCrossentropy(keras.losses.Loss):
    
    def __init__(self, name='ScaledCategoricalCrossentropy', num_categories=10e6, **kwargs):
        super(ScaledCategoricalCrossentropy, self).__init__(name=name, **kwargs)
        self.num_categories = num_categories
        self.loss = keras.losses.SparseCategoricalCrossentropy(from_logits=False)
        
    #--------------------------------------------------------------------------    
    def call(self, y_true, y_pred):
        
        y_true = keras.ops.cast(y_true, dtype=torch.float32)       
        loss = self.loss(y_true, y_pred)        
        scaled_loss = loss * (1 + 1/self.num_categories)    
        
        return scaled_loss
    
    #--------------------------------------------------------------------------    
    def get_config(self):
        base_config = super(ScaledCategoricalCrossentropy, self).get_config()
        return {**base_config, 'name': self.name, 'num_categories': self.num_categories}
    
    @classmethod
    def from_config(cls, config):
        return cls(**config)
    
    
# [METRICS]
###############################################################################
class RouletteAccuracy(keras.metrics.Metric):

    def __init__(self, name='RouletteAccuracy', **kwargs):
        super(RouletteAccuracy, self).__init__(name=name, **kwargs)
        self.total = self.add_weight(name='total', initializer='zeros')
        self.count = self.add_weight(name='count', initializer='zeros')
        
    #--------------------------------------------------------------------------
    def update_state(self, y_true, y_pred, sample_weight=None):
        
        y_true = keras.ops.cast(y_true, dtype=torch.float32)       
        probabilities = keras.ops.argmax(y_pred, axis=1)
        accuracy = keras.ops.equal(y_true, probabilities)               
        
        if sample_weight is not None:
            sample_weight = keras.ops.cast(sample_weight, dtype=torch.float32)
            accuracy = keras.ops.multiply(accuracy, sample_weight)
            
        
        # Update the state variables
        self.total.assign_add(keras.ops.sum(accuracy))
     
    #--------------------------------------------------------------------------
    def result(self):
        return self.total / (self.count + keras.backend.epsilon())
    
    #--------------------------------------------------------------------------
    def reset_states(self):
        self.total.assign(0)
        self.count.assign(0)

    #--------------------------------------------------------------------------
    def get_config(self):
        base_config = super(RouletteAccuracy, self).get_config()
        return {**base_config, 'name': self.name}
    
    @classmethod
    def from_config(cls, config):
        return cls(**config)







