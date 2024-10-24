import keras
from keras import losses, metrics, layers, Model
import torch

from FAIRS.commons.utils.learning.embeddings import PositionalEmbedding
from FAIRS.commons.utils.learning.transformers import TransformerEncoder, TransformerDecoder
from FAIRS.commons.utils.learning.classifiers import SoftMaxClassifier
from FAIRS.commons.utils.learning.metrics import RouletteCategoricalCrossentropy, RouletteAccuracy
from FAIRS.commons.constants import CONFIG, NUMBERS, COLORS
from FAIRS.commons.logger import logger




# [XREP CAPTIONING MODEL]
###############################################################################
class OLDFAIRSnet: 

    def __init__(self):         
             
        self.window_size = CONFIG["dataset"]["PERCEPTIVE_SIZE"] 
        self.embedding_dims = CONFIG["model"]["EMBEDDING_DIMS"]        
        self.num_heads = CONFIG["model"]["NUM_HEADS"]  
        self.num_encoders = CONFIG["model"]["NUM_ENCODERS"] 
        self.num_decoders = CONFIG["model"]["NUM_DECODERS"]
        self.learning_rate = CONFIG["training"]["LEARNING_RATE"]             
        self.xla_state = CONFIG["training"]["XLA_STATE"]  

        # initialize the image encoder and the transformers encoders and decoders
        self.encoder_timeseries = layers.Input(shape=(self.window_size,), name='encoder_timeseries')
        self.decoder_timeseries = layers.Input(shape=(self.window_size,), name='decoder_timeseries')
        self.encoder_positions = layers.Input(shape=(self.window_size,), name='encoder_positions') 
        self.decoder_positions = layers.Input(shape=(self.window_size,), name='decoder_positions')         
                
        self.encoders = [TransformerEncoder(self.embedding_dims, self.num_heads) for _ in range(self.num_encoders)]
        self.decoders = [TransformerDecoder(self.embedding_dims, self.num_heads) for _ in range(self.num_decoders)]
        self.encoder_embeddings = PositionalEmbedding(self.embedding_dims, self.window_size, mask_zero=False) 
        self.decoder_embeddings = PositionalEmbedding(self.embedding_dims, self.window_size, mask_zero=False) 
        self.classifier = SoftMaxClassifier(128, NUMBERS)  
        
    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, model_summary=True):                
       
        # encode images using the convolutional encoder
        pos_emb_encoder = self.encoder_embeddings(self.encoder_timeseries, self.encoder_positions) 
        pos_emb_decoder = self.decoder_embeddings(self.decoder_timeseries, self.decoder_positions) 
        
        # handle the connections between transformers blocks        
        encoder_output = pos_emb_encoder
        decoder_output = pos_emb_decoder    
        for encoder in self.encoders:
            encoder_output = encoder(encoder_output, training=False)
        for decoder in self.decoders:
            decoder_output = decoder(decoder_output, encoder_output, 
                                     training=False, mask=None)

        # apply the softmax classifier layer
        output = self.classifier(decoder_output)        
        
        # define the model from inputs and outputs
        model = Model(inputs=[self.encoder_timeseries, self.encoder_positions,
                              self.decoder_timeseries, self.decoder_positions], 
                      outputs=output)     

        # define model compilation parameters such as learning rate, loss, metrics and optimizer
        loss = [RouletteCategoricalCrossentropy(window_size=self.window_size, 
                                                penalty_increase=CONFIG["training"]["LOSS_PENALTY_FACTOR"])] 
        metric = [metrics.SparseCategoricalAccuracy()]
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)          
        model.compile(loss=loss, optimizer=opt, metrics=metric, COMPILE=self.xla_state)         
        if model_summary:
            model.summary(expand_nested=True)

        return model
    


# [FAIRS CAPTIONING MODEL]
###############################################################################
class FAIRSnet: 

    def __init__(self):  
       
        self.perceptive_size = CONFIG["dataset"]["PERCEPTIVE_SIZE"] 
        self.embedding_dims = CONFIG["model"]["EMBEDDING_DIMS"]        
        self.num_heads = CONFIG["model"]["NUM_HEADS"]  
        self.num_encoders = CONFIG["model"]["NUM_ENCODERS"] 
        self.num_decoders = CONFIG["model"]["NUM_DECODERS"]
        self.jit_compile = CONFIG["model"]["JIT_COMPILE"]
        self.jit_backend = CONFIG["model"]["JIT_BACKEND"]
        self.learning_rate = CONFIG["training"]["LEARNING_RATE"] 
       
        self.action_size = NUMBERS + COLORS - 1                    

        
                    
        
        
    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, model_summary=True):    

        # initialize the image encoder and the transformers encoders and decoders      
        timeseries = layers.Input(shape=(self.perceptive_size,), name='timeseries')            
       
        layer = layers.Dense(24, activation='relu')(timeseries)
        layer = layers.Dense(24, activation='relu')(layer)

        # Output layer for Q-values, one for each possible action
        q_values_output = layers.Dense(self.action_size, activation='linear')(layer)

        # Define the model with input and output
        model = Model(inputs=timeseries, outputs=q_values_output)         

        # define model compilation parameters such as learning rate, loss, metrics and optimizer
        loss = losses.MeanSquaredError() 
        metric = [metrics.SparseCategoricalAccuracy()]
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)          
        model.compile(loss=loss, optimizer=opt, metrics=metric, jit_compile=False)

        if self.jit_compile:
            model = torch.compile(model, backend=self.jit_backend, mode='default')

        if model_summary:
            model.summary(expand_nested=True)

        return model
       



