import keras
from keras import losses, metrics, layers, Model, activations
import torch

from FAIRS.commons.utils.learning.embeddings import RouletteEmbedding
from FAIRS.commons.utils.learning.logits import QScoreNet, AddNorm
from FAIRS.commons.constants import CONFIG, STATES
from FAIRS.commons.logger import logger


# [FAIRS MODEL]
###############################################################################
class FAIRSnet: 

    def __init__(self, configuration):         
        self.perceptive_size = configuration["dataset"]["PERCEPTIVE_SIZE"] 
        self.embedding_dims = configuration["model"]["EMBEDDING_DIMS"] 
        self.neurons = configuration["model"]["UNITS"]                   
        self.jit_compile = configuration["model"]["JIT_COMPILE"]
        self.jit_backend = configuration["model"]["JIT_BACKEND"]
        self.learning_rate = configuration["training"]["LEARNING_RATE"]       
        self.seed = configuration["SEED"]
       
        self.action_size = STATES
        self.timeseries = layers.Input(shape=(self.perceptive_size,), name='timeseries')        
        self.embedding = RouletteEmbedding(self.embedding_dims, self.action_size, mask_negative=True)
        self.QNet = QScoreNet(self.neurons, self.action_size, self.seed)   
        
        
    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, model_summary=True):    

        # initialize the image encoder and the transformers encoders and decoders      
        timeseries = layers.Input(shape=(self.perceptive_size,), name='timeseries', dtype=torch.int32)
               
        # add layer for frequency embedding
       
        embeddings = self.embedding(timeseries)
        res = layers.Dense(self.neurons, kernel_initializer='he_uniform')(embeddings)             
        layer = layers.Dense(self.neurons, kernel_initializer='he_uniform')(res)                      
        layer = AddNorm()([res, layer])
        layer = activations.relu(layer)  

        res = layers.Dense(self.neurons//2, kernel_initializer='he_uniform')(layer)             
        layer = layers.Dense(self.neurons//2, kernel_initializer='he_uniform')(res)                      
        layer = AddNorm()([res, layer])
        layer = activations.relu(layer)      
        
        layer = layers.Flatten()(layer)
        res = layers.Dense(self.neurons*2, kernel_initializer='he_uniform')(layer)    
        layer = layers.Dense(self.neurons*2, kernel_initializer='he_uniform')(res)
        layer = AddNorm()([res, layer])
        layer = activations.relu(layer)              
        output = self.QNet(layer)         
        
        # define the model from inputs and outputs
        model = Model(inputs=timeseries, outputs=output)                

        # define model compilation parameters such as learning rate, loss, metrics and optimizer
        loss = losses.MeanSquaredError() 
        metric = [metrics.MeanAbsolutePercentageError()]
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)          
        model.compile(loss=loss, optimizer=opt, metrics=metric, jit_compile=False)

        if self.jit_compile:
            model = torch.compile(model, backend=self.jit_backend, mode='default')

        if model_summary:
            model.summary(expand_nested=True)

        return model           
       
       