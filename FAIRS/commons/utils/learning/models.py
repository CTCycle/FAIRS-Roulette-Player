import keras
from keras import losses, metrics, layers, Model

from FAIRS.commons.utils.learning.embeddings import PositionalEmbedding
from FAIRS.commons.utils.learning.transformers import TransformerEncoder, TransformerDecoder
from FAIRS.commons.utils.learning.classifiers import SoftMaxClassifier
from FAIRS.commons.utils.learning.metrics import RouletteCategoricalCrossentropy, RouletteAccuracy
from FAIRS.commons.constants import CONFIG, STATES, COLORS
from FAIRS.commons.logger import logger


# [XREP CAPTIONING MODEL]
###############################################################################
class FAIRSnet: 

    def __init__(self):         
             
        self.window_size = CONFIG["dataset"]["WINDOW_SIZE"] 
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
        self.classifier = SoftMaxClassifier(256, STATES)  
        
    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, summary=True):                
       
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
        model.compile(loss=loss, optimizer=opt, metrics=metric, jit_compile=self.xla_state)         
        if summary:
            model.summary(expand_nested=True)

        return model
       



