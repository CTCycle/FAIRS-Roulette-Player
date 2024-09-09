import keras
from keras import activations, layers
import torch

from FAIRS.commons.constants import CONFIG


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

# [POOLING CONVOLUTIONAL BLOCKS]
###############################################################################
@keras.utils.register_keras_serializable(package='CustomLayers', name='PooledConv')
class PooledConv(layers.Layer):
    
    def __init__(self, units, num_layers=2, **kwargs):
        super(PooledConv, self).__init__(**kwargs)
        self.units = units        
        self.num_layers = num_layers        
        self.pooling = layers.AveragePooling2D(pool_size=(2,2), padding='same')       
        self.convolutions = [layers.Conv2D(units, kernel_size=(3,3), strides=(1,1), padding='same', 
                                           activation=None) for _ in range(num_layers)]  
        self.batch_norm_layers = [layers.BatchNormalization() for _ in range(num_layers)]                 
        
    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------
    def call(self, inputs, training=None):
        layer = inputs
        for conv, bn in zip(self.convolutions, self.batch_norm_layers):
            layer = conv(layer)
            layer = bn(layer, training=training)
            layer = activations.relu(layer) 
        output = self.pooling(layer)           
        
        return output
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(PooledConv, self).get_config()
        config.update({'units': self.units,                       
                       'num_layers': self.num_layers})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)  
    

# [POOLING CONVOLUTIONAL BLOCKS]
###############################################################################
@keras.utils.register_keras_serializable(package='CustomLayers', name='TransposeConv')
class TransposeConv(layers.Layer):

    def __init__(self, units, num_layers=3, **kwargs):
        super(TransposeConv, self).__init__(**kwargs)
        self.units = units        
        self.num_layers = num_layers              
        self.upsamp = layers.UpSampling2D(size=(2,2))
        self.convolutions = [layers.Conv2DTranspose(units, kernel_size=(3,3), strides=(1,1), padding='same',  
                                                    activation=None) for _ in range(num_layers)]
        self.batch_norm_layers = [layers.BatchNormalization() for _ in range(num_layers)]             
        
    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------
    def call(self, inputs, training=None):
        layer = inputs
        for conv, bn in zip(self.convolutions, self.batch_norm_layers):
            layer = conv(layer) 
            layer = bn(layer, training=training)
            layer = activations.relu(layer)
        output = self.upsamp(layer)           
        
        return output   
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(TransposeConv, self).get_config()
        config.update({'units': self.units,                  
                       'num_layers': self.num_layers})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)     

       

# [POOLING CONVOLUTIONAL BLOCKS]
###############################################################################
@keras.utils.register_keras_serializable(package='CustomLayers', name='SobelFilterConv')
class SobelFilterConv(layers.Layer):
    
    def __init__(self, **kwargs):
        super(SobelFilterConv, self).__init__(**kwargs)
        self.sobel_x = keras.ops.convert_to_tensor([[[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
                                                    [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
                                                    [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]], 
                                                    dtype=torch.float32)
        self.sobel_y = keras.ops.convert_to_tensor([[[-1, -2, -1], [0, 0, 0], [1, 2, 1]],
                                                    [[-1, -2, -1], [0, 0, 0], [1, 2, 1]],
                                                    [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]], 
                                                    dtype=torch.float32)
        self.sobel_x = keras.ops.expand_dims(self.sobel_x, axis=-1)
        self.sobel_y = keras.ops.expand_dims(self.sobel_y, axis=-1)
        
    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------
    def call(self, inputs, training=None):
        # Apply the Sobel filter for x and y directions
        Gx = keras.ops.conv(inputs, self.sobel_x, padding="same", strides=(1,1))
        Gy = keras.ops.conv(inputs, self.sobel_y, padding="same", strides=(1,1))

        # Calculate the magnitude of the gradients
        gradients = keras.ops.sqrt(keras.ops.square(Gx) + keras.ops.square(Gy))
        
        # Optionally normalize the output
        gradients = gradients / keras.ops.amax(gradients)  
        
        return gradients
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(SobelFilterConv, self).get_config()
        config.update({})
        return config

    # deserialization method 
    #--------------------------------------------------------------------------
    @classmethod
    def from_config(cls, config):
        return cls(**config)  

    


  
    



