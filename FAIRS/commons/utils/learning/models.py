import keras
from keras import losses, metrics, layers, Model, activations
import torch

from FAIRS.commons.utils.learning.embeddings import RouletteEmbedding
from FAIRS.commons.utils.learning.logits import BatchNormDense, InverseFrequency, QScoreNet, AddNorm
from FAIRS.commons.constants import CONFIG, STATES
from FAIRS.commons.logger import logger


# [FAIRS MODEL]
###############################################################################
class FAIRSnet: 

    def __init__(self, configuration):         
        self.perceptive_size = configuration["model"]["PERCEPTIVE_FIELD"] 
        self.embedding_dims = configuration["model"]["EMBEDDING_DIMS"] 
        self.neurons = configuration["model"]["UNITS"]                   
        self.jit_compile = configuration["model"]["JIT_COMPILE"]
        self.jit_backend = configuration["model"]["JIT_BACKEND"]
        self.learning_rate = configuration["training"]["LEARNING_RATE"]       
        self.seed = configuration["SEED"]
       
        self.action_size = STATES
        self.timeseries = layers.Input(
            shape=(self.perceptive_size,), name='timeseries')        
        self.embedding = RouletteEmbedding(
            self.embedding_dims, self.action_size, mask_negative=True)
        
        self.q_neurons = self.neurons * 2
        self.QNet = QScoreNet(self.q_neurons, self.action_size, self.seed)   
        
        
    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, model_summary=True): 
        # initialize the image encoder and the transformers encoders and decoders      
        timeseries = layers.Input(
            shape=(self.perceptive_size,), name='timeseries', dtype=torch.int32)  

        inverse_freq = InverseFrequency()(timeseries)
        inverse_freq = keras.ops.expand_dims(inverse_freq, axis=-1)  
        inverse_freq = BatchNormDense(self.neurons)(inverse_freq)
                
        embeddings = self.embedding(timeseries)
        layer = BatchNormDense(self.neurons)(embeddings)
        layer = BatchNormDense(self.neurons)(layer)  
        layer = BatchNormDense(self.neurons)(layer) 

        layer = AddNorm([layer, inverse_freq])      
        
        layer = layers.Flatten()(layer)
        layer = BatchNormDense(self.q_neurons)(layer)
        layer = layers.Dropout(rate=0.3, seed=self.seed)(layer) 
        output = self.QNet(layer)         
        
        # define the model from inputs and outputs
        model = Model(inputs=timeseries, outputs=output)                

        # define model compilation parameters such as learning rate, loss, metrics and optimizer
        loss = losses.MeanSquaredError() 
        metric = [metrics.RootMeanSquaredError()]
        opt = keras.optimizers.AdamW(learning_rate=self.learning_rate)          
        model.compile(loss=loss, optimizer=opt, metrics=metric, jit_compile=False)

        if model_summary:
            model.summary(expand_nested=True)
            
        if self.jit_compile:
            model = torch.compile(model, backend=self.jit_backend, mode='default')

        

        return model           
       
       