import torch
import keras
import tensorflow as tf

from FAIRS.commons.utils.preprocessing.mapping import RouletteMapper
from FAIRS.commons.constants import CONFIG, STATES, COLORS
from FAIRS.commons.logger import logger

# [LOSS FUNCTION]
###############################################################################
class RouletteCategoricalCrossentropy(keras.losses.Loss):
    
    def __init__(self, name='RouletteCategoricalCrossentropy', num_categories=10e6, penalty_factor=1.0, **kwargs):
        super(RouletteCategoricalCrossentropy, self).__init__(name=name, **kwargs)
        self.num_categories = num_categories
        self.penalty_factor = penalty_factor
        mapper = RouletteMapper()
        self.roulette_mapping = mapper.position_map
        self.loss = keras.losses.SparseCategoricalCrossentropy(from_logits=False)

    # Calculates a penalty based on the difference between the predicted
    # and true values using the roulette mapping.
    #--------------------------------------------------------------------------
    def calculate_penalty(self, y_true, y_pred):
        
        true_value = y_true.item()  # Assuming y_true is a single value
        pred_value = torch.argmax(y_pred).item()  # Get the index of the predicted category

        # Calculate the difference in positions using the roulette mapping
        true_position = self.roulette_mapping.get(true_value, 0)
        pred_position = self.roulette_mapping.get(pred_value, 0)
        distance = abs(true_position - pred_position)

        # Apply a penalty based on the distance
        penalty = self.penalty_factor * distance
        return penalty

    #--------------------------------------------------------------------------    
    def call(self, y_true, y_pred):
        y_true = keras.ops.cast(y_true, dtype=torch.float32)
        loss = self.loss(y_true, y_pred)        
        # Apply penalty based on the difference between prediction and true value
        penalty = self.calculate_penalty(y_true, y_pred)
        total_loss = loss + penalty
        
        return total_loss
    
    #--------------------------------------------------------------------------    
    def get_config(self):
        base_config = super(RouletteCategoricalCrossentropy, self).get_config()
        return {**base_config, 'name': self.name, 'num_categories': self.num_categories, 'roulette_mapping': self.roulette_mapping, 'penalty_factor': self.penalty_factor}
    
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







