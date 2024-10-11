import keras
from keras import losses, metrics, layers, Model

from FAIRS.commons.utils.learning.embeddings import PositionalEmbedding
from FAIRS.commons.utils.learning.transformers import TransformerEncoder, TransformerDecoder
from FAIRS.commons.utils.learning.classifiers import SoftMaxClassifier
from FAIRS.commons.utils.learning.metrics import RouletteCategoricalCrossentropy, RouletteAccuracy
from FAIRS.commons.constants import CONFIG, STATES, COLORS
from FAIRS.commons.logger import logger


# [FAIRS CAPTIONING MODEL]
###############################################################################
class FAIRSnet: 

    def __init__(self):  

        
       
        self.window_size = CONFIG["dataset"]["WINDOW_SIZE"] 
        self.embedding_dims = CONFIG["model"]["EMBEDDING_DIMS"]        
        self.num_heads = CONFIG["model"]["NUM_HEADS"]  
        self.num_encoders = CONFIG["model"]["NUM_ENCODERS"] 
        self.num_decoders = CONFIG["model"]["NUM_DECODERS"]
        self.learning_rate = CONFIG["training"]["LEARNING_RATE"] 

        self.state_size = 1
        self.action_size = 20                        

        self.xla_state = CONFIG["training"]["XLA_STATE"]  

        # initialize the image encoder and the transformers encoders and decoders
        self.positions = layers.Input(shape=(self.window_size,), name='positions')
        self.timeseries = layers.Input(shape=(self.window_size,), name='timeseries')
        self.colors = layers.Input(shape=(self.window_size,), name='colors')                    
        
        
    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, summary=True):                
       
        layer = layers.Dense(24, activation='relu')(self.positions)
        layer = layers.Dense(24, activation='relu')(layer)

        # Output layer for Q-values, one for each possible action
        q_values_output = layers.Dense(self.action_size, activation='linear')(layer)

        # Define the model with input and output
        model = Model(inputs=self.positions, outputs=q_values_output)         

        # define model compilation parameters such as learning rate, loss, metrics and optimizer
        loss = losses.MeanSquaredError() 
        metric = [metrics.SparseCategoricalAccuracy()]
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)          
        model.compile(loss=loss, optimizer=opt, metrics=metric, jit_compile=self.xla_state)

        if summary:
            model.summary(expand_nested=True)

        return model
       



