import keras
from keras import losses, metrics, layers, Model, activations
import torch

from FAIRS.commons.utils.learning.models.embeddings import RouletteEmbedding
from FAIRS.commons.utils.learning.models.logits import BatchNormDense, InverseFrequency, QScoreNet, AddNorm
from FAIRS.commons.constants import CONFIG, STATES, NUMBERS
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
        self.q_neurons = self.neurons * 2
       
        self.action_size = STATES
        self.add_norm = AddNorm() 
        self.gain = layers.Input(shape=(), name='gain', dtype='int32')
        self.timeseries = layers.Input(
            shape=(self.perceptive_size,), name='timeseries', dtype='int32')              
        self.embedding = RouletteEmbedding(
            self.embedding_dims, NUMBERS, mask_padding=True)        
               
        self.QNet = QScoreNet(self.q_neurons, self.action_size, self.seed)         
        
    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, model_summary=True):                
        embeddings = self.embedding(self.timeseries)
        layer = BatchNormDense(self.neurons)(embeddings)
        layer = BatchNormDense(self.neurons//2)(layer)  

        gain = keras.ops.expand_dims(self.gain, axis=-1)
        gain = BatchNormDense(self.neurons//2)(gain)        
        add = self.add_norm([gain, layer])               
        
        layer = layers.Flatten()(add)
        layer = BatchNormDense(self.q_neurons)(layer)
        layer = layers.Dropout(rate=0.3, seed=self.seed)(layer) 
        output = self.QNet(layer)         
        
        # define the model from inputs and outputs
        model = Model(inputs=[self.timeseries, self.gain], outputs=output)                

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
       
       