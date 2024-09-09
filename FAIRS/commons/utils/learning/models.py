import keras
from keras import layers, Model


from FAIRS.commons.utils.learning.embeddings import PositionalEmbedding
from FAIRS.commons.utils.learning.transformers import TransformerEncoder, ReformingEncoder
from FAIRS.commons.utils.learning.classifiers import NumberPredictor, ColorPredictor
from FAIRS.commons.utils.learning.metrics import HybridCategoricalCrossentropy, RouletteAccuracy
from FAIRS.commons.constants import CONFIG, STATES, COLORS
from FAIRS.commons.logger import logger


# [XREP CAPTIONING MODEL]
###############################################################################
class FAIRSnet: 

    def __init__(self):         
             
        self.window_size = CONFIG["dataset"]["WINDOW_SIZE"] 
        self.embedding_dims = CONFIG["model"]["EMBEDDING_DIMS"]
        self.kernel_size = CONFIG["model"]["CONVOLUTIONAL_KERNEL"]
        self.num_heads = CONFIG["model"]["NUM_HEADS"]  
        self.num_encoders = CONFIG["model"]["NUM_ENCODERS"] 
        self.learning_rate = CONFIG["training"]["LEARNING_RATE"]             
        self.xla_state = CONFIG["training"]["XLA_STATE"]  

        # initialize the image encoder and the transformers encoders and decoders
        self.sequence_inputs = layers.Input(shape=(self.window_size,), name='sequence_inputs')
        self.position_inputs = layers.Input(shape=(self.window_size,), name='position_inputs') 
                
        self.encoders = [TransformerEncoder(self.embedding_dims, self.num_heads) for _ in range(self.num_encoders)]
        self.reformer = ReformingEncoder(self.embedding_dims, self.kernel_size)
        self.embeddings = PositionalEmbedding(self.embedding_dims, self.window_size, mask_zero=False) 
        self.number_predictor = NumberPredictor(128, STATES)  
        self.color_predictor = ColorPredictor(64, COLORS)                

    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, summary=True):                
       
        # encode images using the convolutional encoder              
        embeddings = self.embeddings(self.sequence_inputs, self.position_inputs)    
        for encoder in self.encoders:
            embeddings = encoder(embeddings, training=False) 

        layer = self.reformer(embeddings)

        # apply the softmax classifier layer
        predicted_numbers = self.number_predictor(layer)    
        predicted_colors = self.color_predictor(layer) 
        outputs = (predicted_numbers, predicted_colors)

        # define the model from inputs and outputs
        model = Model(inputs=[self.sequence_inputs, self.position_inputs], outputs=outputs)     

        # define model compilation parameters such as learning rate, loss, metrics and optimizer
        loss = HybridCategoricalCrossentropy()  
        metric = [RouletteAccuracy(), RouletteAccuracy()]
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)          
        model.compile(loss=loss, optimizer=opt, metrics=metric, jit_compile=self.xla_state)         
        if summary:
            model.summary(expand_nested=True)

        return model
       



