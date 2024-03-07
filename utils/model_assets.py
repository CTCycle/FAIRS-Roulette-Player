import os
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from tensorflow import keras
from keras.models import Model
from keras import layers
from sklearn.metrics import confusion_matrix, roc_curve, auc
from sklearn.preprocessing import label_binarize



# [CALLBACK FOR REAL TIME TRAINING MONITORING]
#==============================================================================
# Callback to check real time model history and visualize it through custom plot
#==============================================================================
class RealTimeHistory(keras.callbacks.Callback):
    
    ''' 
    A class including the callback to show a real time plot of the training history. 
      
    Methods:
        
    __init__(plot_path): initializes the class with the plot savepath       
    
    ''' 
    def __init__(self, plot_path, validation=True):        
        super().__init__()
        self.plot_path = plot_path
        self.epochs = []
        self.loss_hist = []
        self.metric_hist = []
        self.loss_val_hist = []        
        self.metric_val_hist = []
        self.validation = validation            
    
    def on_epoch_end(self, epoch, logs = {}):
        if epoch % 10 == 0:                    
            self.epochs.append(epoch)
            self.loss_hist.append(logs[list(logs.keys())[0]])
            self.metric_hist.append(logs[list(logs.keys())[1]])
            if self.validation==True:
                self.loss_val_hist.append(logs[list(logs.keys())[2]])            
                self.metric_val_hist.append(logs[list(logs.keys())[3]])
        if epoch % 40 == 0:           
            fig_path = os.path.join(self.plot_path, 'training_history.jpeg')
            plt.subplot(2, 1, 1)
            plt.plot(self.epochs, self.loss_hist, label='training loss')
            if self.validation==True:
                plt.plot(self.epochs, self.loss_val_hist, label='validation loss')
                plt.legend(loc = 'best', fontsize = 8)
            plt.title('Loss plot')
            plt.ylabel('Categorical Crossentropy')
            plt.xlabel('epoch')
            plt.subplot(2, 1, 2)
            plt.plot(self.epochs, self.metric_hist, label='train metrics') 
            if self.validation==True: 
                plt.plot(self.epochs, self.metric_val_hist, label='validation metrics') 
                plt.legend(loc = 'best', fontsize = 8)
            plt.title('metrics plot')
            plt.ylabel('Categorical accuracy')
            plt.xlabel('epoch')       
            plt.tight_layout()
            plt.savefig(fig_path, bbox_inches = 'tight', format = 'jpeg', dpi = 300)
            plt.close()

                  
# [POSITION EMBEDDING]
#==============================================================================
# Positional embedding custom layer
#==============================================================================
@keras.utils.register_keras_serializable(package='CustomLayers', name='PositionalEmbedding')
class PositionalEmbedding(layers.Layer):
    def __init__(self, sequence_length, vocab_size, embedding_dims, mask_zero=None, **kwargs):
        super(PositionalEmbedding, self).__init__(**kwargs)
        self.sequence_length = sequence_length
        self.vocab_size = vocab_size
        self.embedding_dims = embedding_dims
        self.mask_zero = mask_zero
        self.word_embedding_layer = layers.Embedding(input_dim=vocab_size, output_dim=embedding_dims)
        self.position_embedding_layer = layers.Embedding(input_dim=sequence_length, output_dim=embedding_dims)
 
    # implement positional embedding through call method  
    #--------------------------------------------------------------------------    
    def call(self, inputs):        
        position_indices = tf.range(tf.shape(inputs)[-1])
        embedded_words = self.word_embedding_layer(inputs)
        embedded_indices = self.position_embedding_layer(position_indices)

        return embedded_words + embedded_indices
    
    # compute the mask for padded sequences  
    #--------------------------------------------------------------------------
    def compute_mask(self, inputs, mask=None):
        return tf.math.not_equal(inputs, 0)
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(PositionalEmbedding, self).get_config()
        config.update({'sequence_length': self.sequence_length,
                       'vocab_size': self.vocab_size,
                       'embedding_dims': self.embedding_dims,
                       'mask_zero': self.mask_zero})
        return config

    @classmethod
    def from_config(cls, config):
        return cls(**config)
    
    
# [CONVOLUTIONAL BLOCK  ]
#==============================================================================
# Positional embedding custom layer
#==============================================================================
@keras.utils.register_keras_serializable(package='CustomLayers', name='ConvFeedForward')
class ConvFeedForward(keras.layers.Layer):
    def __init__(self, kernel_size, **kwargs):
        super(ConvFeedForward, self).__init__(**kwargs)
        self.kernel_size = kernel_size
        self.conv1 = layers.Conv1D(128, kernel_size=kernel_size, padding='same', activation='relu')
        self.conv2 = layers.Conv1D(256, kernel_size=kernel_size, padding='same', activation='relu')
        self.conv3 = layers.Conv1D(512, kernel_size=kernel_size, padding='same', activation='relu')         
        self.layernorm = layers.LayerNormalization()
        self.dense = layers.Dense(512, activation='relu', kernel_initializer='he_uniform')          

    # implement positional embedding through call method  
    #--------------------------------------------------------------------------
    def call(self, inputs, training=True):
        layer = self.conv1(inputs)       
        layer = self.conv2(layer)       
        layer = self.conv3(layer)
        layer = self.layernorm(inputs + layer)
        output = self.dense(layer)

        return output
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(ConvFeedForward, self).get_config()
        config.update({'kernel_size': self.kernel_size})
        return config

    @classmethod
    def from_config(cls, config):
        return cls(**config)
        
# [TRANSFORMER ENCODER]
#==============================================================================
# Custom transformer encoder
#============================================================================== 
@keras.utils.register_keras_serializable(package='CustomLayers', name='TransformerEncoder')
class TransformerEncoder(keras.layers.Layer):
    def __init__(self, embedding_dims, num_heads, **kwargs):
        super(TransformerEncoder, self).__init__(**kwargs)
        self.embedding_dims = embedding_dims       
        self.num_heads = num_heads        
        self.attention = layers.MultiHeadAttention(num_heads=num_heads, key_dim=self.embedding_dims)
        self.layernorm1 = layers.LayerNormalization()
        self.layernorm2 = layers.LayerNormalization()
        self.dense1 = layers.Dense(512, activation='relu', kernel_initializer='he_uniform')
        self.dense2 = layers.Dense(512, activation='relu', kernel_initializer='he_uniform')        

    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------
    def call(self, inputs, training=True):        
        inputs = self.layernorm1(inputs)
        inputs = self.dense1(inputs)       
        attention_output = self.attention(query=inputs, value=inputs, key=inputs,
                                          attention_mask=None, training=training)                
        layernorm = self.layernorm2(inputs + attention_output)
        output = self.dense2(layernorm)       
        return output
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(TransformerEncoder, self).get_config()
        config.update({'embedding_dims': self.embedding_dims,
                       'num_heads': self.num_heads})
        return config

    @classmethod
    def from_config(cls, config):
        return cls(**config)       

# [BATCH NORMALIZED FFW]
#==============================================================================
# Custom layer
#============================================================================== 
@keras.utils.register_keras_serializable(package='CustomLayers', name='BNFeedForward')
class BNFeedForward(keras.layers.Layer):
    def __init__(self, units, seed=42, dropout=0.1, **kwargs):
        super(BNFeedForward, self).__init__(**kwargs)
        self.units = units   
        self.seed = seed  
        self.dropout = dropout
        self.BN = layers.BatchNormalization(axis=-1, epsilon=0.001)  
        self.drop = layers.Dropout(rate=dropout, seed=seed)      
        self.dense = layers.Dense(units, activation='relu', kernel_initializer='he_uniform')
        
    # implement transformer encoder through call method  
    #--------------------------------------------------------------------------
    def call(self, inputs, training=True):        
        layer = self.dense(inputs)
        layer = self.BN(layer, training=training)       
        output = self.drop(layer, training=training)                
        
        return output
    
    # serialize layer for saving  
    #--------------------------------------------------------------------------
    def get_config(self):
        config = super(BNFeedForward, self).get_config()
        config.update({'units': self.units,
                       'seed': self.seed,
                       'dropout': self.dropout})
        return config

    @classmethod
    def from_config(cls, config):
        return cls(**config)      


# [COLOR CODE MODEL]
#==============================================================================
# collection of model and submodels
#==============================================================================
class ColorCodeModel:

    def __init__(self, learning_rate, window_size, embedding_dims, 
                 num_blocks, num_heads, kernel_size, seed, XLA_state):

        self.learning_rate = learning_rate
        self.window_size = window_size             
        self.embedding_dims = embedding_dims
        self.num_blocks = num_blocks
        self.num_heads = num_heads
        self.kernel_size = kernel_size         
        self.seed = seed       
        self.XLA_state = XLA_state        
        self.posembedding = PositionalEmbedding(self.window_size, 3, self.embedding_dims)
        self.encoders = [TransformerEncoder(self.embedding_dims, self.num_heads) for i in range(self.num_blocks)]
        self.ffns = [ConvFeedForward(self.kernel_size) for i in range(self.num_blocks)]        

    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, summary=True):          
        sequence_input = layers.Input(shape=(self.window_size, 1))                              
        layer = self.posembedding(sequence_input)  
        layer = layers.Reshape((self.window_size, self.embedding_dims))(layer)      
        for encoder, ffn in zip(self.encoders, self.ffns):
            layer = encoder(layer)
            layer = ffn(layer) 
        pooling = layers.GlobalAveragePooling1D()(layer)       
        layer = BNFeedForward(512, self.seed, 0.1)(pooling)
        layer = BNFeedForward(256, self.seed, 0.1)(layer)
        layer = BNFeedForward(128, self.seed, 0.1)(layer)        
        output = layers.Dense(3, activation='softmax', dtype='float32')(layer)        
       
        model = Model(inputs = sequence_input, outputs = output, name = 'CCM')    
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)
        loss = keras.losses.CategoricalCrossentropy(from_logits=False)
        metrics = keras.metrics.CategoricalAccuracy()
        model.compile(loss = loss, optimizer = opt, metrics = metrics,
                      jit_compile=self.XLA_state) 
        if summary==True:
            model.summary(expand_nested=True)

        return model
     

# [NUM MATRIX MODEL]
#==============================================================================
# collection of model and submodels
#==============================================================================
class NumMatrixModel:

    def __init__(self, learning_rate, window_size, embedding_dims, 
                 num_blocks, num_heads, kernel_size, seed, XLA_state):

        self.learning_rate = learning_rate
        self.window_size = window_size               
        self.embedding_dims = embedding_dims
        self.num_blocks = num_blocks
        self.num_heads = num_heads
        self.kernel_size = kernel_size         
        self.seed = seed       
        self.XLA_state = XLA_state        
        self.encoderseq = [TransformerEncoder(self.embedding_dims, self.num_heads) for i in range(self.num_blocks)]
        self.encoderpos = [TransformerEncoder(self.embedding_dims, self.num_heads) for i in range(self.num_blocks)]
        self.ffnseq = [ConvFeedForward(self.kernel_size) for i in range(self.num_blocks)]  
        self.ffnpos = [ConvFeedForward(self.kernel_size) for i in range(self.num_blocks)] 

    # build model given the architecture
    #--------------------------------------------------------------------------
    def get_model(self, summary=True):      
        sequence_input = layers.Input(shape=(self.window_size, 1))
        position_input = layers.Input(shape=(self.window_size, 1))
        embeddingseq = PositionalEmbedding(self.window_size, 37, self.embedding_dims)(sequence_input)
        layerseq = layers.Reshape((self.window_size, self.embedding_dims))(embeddingseq)
        embeddingpos = PositionalEmbedding(self.window_size, 37, self.embedding_dims)(position_input)
        layerpos = layers.Reshape((self.window_size, self.embedding_dims))(embeddingpos)        
        for encoder, ffn in zip(self.encoderseq, self.ffnseq):
            layerseq = encoder(layerseq)
            layerseq = ffn(layerseq)                
        for encoder, ffn in zip(self.encoderpos, self.ffnpos):
            layerpos = encoder(layerpos)
            layerpos = ffn(layerpos) 
        layerseq = layers.GlobalAveragePooling1D()(layerseq) 
        layerpos = layers.GlobalAveragePooling1D()(layerpos)       
        add = layers.Add()([layerseq, layerpos])        
        layer = BNFeedForward(512, self.seed, 0.1)(add)
        layer = BNFeedForward(128, self.seed, 0.1)(layer)        
        output = layers.Dense(37, activation='softmax', dtype='float32')(layer)

        model = Model(inputs = [sequence_input, position_input], outputs = output, name = 'NMM')    
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)
        loss = keras.losses.CategoricalCrossentropy(from_logits=False)
        metrics = keras.metrics.CategoricalAccuracy()
        model.compile(loss = loss, optimizer = opt, metrics = metrics,
                      jit_compile=self.XLA_state)
        if summary==True:
            model.summary(expand_nested=True)      
        
        return model       


# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
#==============================================================================
# Collection of methods for machine learning training and tensorflow settings
#==============================================================================
class ModelTraining:    
       
    def __init__(self, device = 'default', seed=42, use_mixed_precision=False):                     
        np.random.seed(seed)
        tf.random.set_seed(seed)         
        self.available_devices = tf.config.list_physical_devices()
        print('-------------------------------------------------------------------------------')        
        print('The current devices are available: ')
        print('-------------------------------------------------------------------------------')
        for dev in self.available_devices:
            print()
            print(dev)
        print()
        print('-------------------------------------------------------------------------------')
        if device == 'GPU':
            self.physical_devices = tf.config.list_physical_devices('GPU')
            if not self.physical_devices:
                print('No GPU found. Falling back to CPU')
                tf.config.set_visible_devices([], 'GPU')
            else:
                if use_mixed_precision == True:
                    policy = keras.mixed_precision.Policy('mixed_float16')
                    keras.mixed_precision.set_global_policy(policy) 
                tf.config.set_visible_devices(self.physical_devices[0], 'GPU') 
                #os.environ['TF_GPU_ALLOCATOR']='cuda_malloc_async'                  
                print('GPU is set as active device')
            print('-------------------------------------------------------------------------------')
            print()        
        elif device == 'CPU':
            tf.config.set_visible_devices([], 'GPU')
            print('CPU is set as active device')
            print('-------------------------------------------------------------------------------')
            print()
    
    #-------------------------------------------------------------------------- 
    def model_parameters(self, parameters_dict, savepath):

        '''
        Saves the model parameters to a JSON file. The parameters are provided 
        as a dictionary and are written to a file named 'model_parameters.json' 
        in the specified directory.

        Keyword arguments:
            parameters_dict (dict): A dictionary containing the parameters to be saved.
            savepath (str): The directory path where the parameters will be saved.

        Returns:
            None       

        '''
        path = os.path.join(savepath, 'model_parameters.json')      
        with open(path, 'w') as f:
            json.dump(parameters_dict, f)    


# [MODEL VALIDATION]
#============================================================================== 
# Methods for model validation
#==============================================================================
class ModelValidation:

    def __init__(self, model):      
        self.model = model       
    
    # comparison of data distribution using statistical methods 
    #--------------------------------------------------------------------------     
    def FAIRS_confusion(self, Y_real, predictions, name, path, dpi=400):         
        cm = confusion_matrix(Y_real, predictions)    
        fig, ax = plt.subplots()        
        sns.heatmap(cm, annot=True, fmt='d', ax=ax, cmap=plt.cm.Blues, cbar=False)        
        ax.set_xlabel('Predicted labels')
        ax.set_ylabel('True labels')
        ax.set_title('Confusion Matrix')
        ax.set_xticks(np.arange(len(np.unique(Y_real))))
        ax.set_yticks(np.arange(len(np.unique(predictions))))
        ax.set_xticklabels(np.unique(Y_real))
        ax.set_yticklabels(np.unique(predictions))
        plt.tight_layout()
        plot_loc = os.path.join(path, f'{name}.jpeg')
        plt.savefig(plot_loc, bbox_inches='tight', format='jpeg', dpi = dpi)

    # comparison of data distribution using statistical methods 
    #--------------------------------------------------------------------------
    def plot_multi_ROC(Y_real, predictions, class_dict, path, dpi):
    
        Y_real_bin = label_binarize(Y_real, classes=list(class_dict.values()))
        n_classes = Y_real_bin.shape[1]        
        fpr = dict()
        tpr = dict()
        roc_auc = dict()
        for i in range(n_classes):
            fpr[i], tpr[i], _ = roc_curve(Y_real_bin[:, i], predictions[:, i])
            roc_auc[i] = auc(fpr[i], tpr[i])    
        plt.figure()
        for i in range(n_classes):
            plt.plot(fpr[i], tpr[i], label='ROC curve of class {0} (area = {1:0.2f})'
                 ''.format(list(class_dict.keys())[i], roc_auc[i]))
        plt.plot([0, 1], [0, 1], 'k--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('Some extension of Receiver operating characteristic to multi-class')
        plt.legend(loc='lower right')       
        plot_loc = os.path.join(path, 'multi_ROC.jpeg')
        plt.savefig(plot_loc, bbox_inches='tight', format='jpeg', dpi=dpi)           
    

