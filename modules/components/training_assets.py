import os
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from tensorflow import keras
from keras import regularizers
from keras.models import Model
from keras.layers import Dense, Conv1D, MaxPooling1D, Dropout, LSTM, BatchNormalization, Add
from keras.layers import Embedding, Reshape, Input, RepeatVector, TimeDistributed
from sklearn.metrics import confusion_matrix, roc_curve, auc
from sklearn.preprocessing import label_binarize


# [CALLBACK FOR REAL TIME TRAINING MONITORING]
#==============================================================================
# Callback to check real time model history and visualize it through custom plot
#==============================================================================
class RealTimeHistory(keras.callbacks.Callback):
    
    """ 
    A class including the callback to show a real time plot of the training history. 
      
    Methods:
        
    __init__(plot_path): initializes the class with the plot savepath       
    
    """   
    def __init__(self, plot_path, validation=True):        
        super().__init__()
        self.plot_path = plot_path
        self.epochs = []
        self.loss_hist = []
        self.metric_hist = []
        self.loss_val_hist = []        
        self.metric_val_hist = []
        self.validation = validation            
    #--------------------------------------------------------------------------
    def on_epoch_end(self, epoch, logs = {}):
        if epoch % 10 == 0:                    
            self.epochs.append(epoch)
            self.loss_hist.append(logs[list(logs.keys())[0]])
            self.metric_hist.append(logs[list(logs.keys())[1]])
            if self.validation==True:
                self.loss_val_hist.append(logs[list(logs.keys())[2]])            
                self.metric_val_hist.append(logs[list(logs.keys())[3]])
        if epoch % 40 == 0:            
            #------------------------------------------------------------------
            fig_path = os.path.join(self.plot_path, 'training_history.jpeg')
            plt.subplot(2, 1, 1)
            plt.plot(self.epochs, self.loss_hist, label = 'training loss')
            if self.validation==True:
                plt.plot(self.epochs, self.loss_val_hist, label = 'validation loss')
                plt.legend(loc = 'best', fontsize = 8)
            plt.title('Loss plot')
            plt.ylabel('Categorical Crossentropy')
            plt.xlabel('epoch')
            plt.subplot(2, 1, 2)
            plt.plot(self.epochs, self.metric_hist, label = 'train metrics') 
            if self.validation==True: 
                plt.plot(self.epochs, self.metric_val_hist, label = 'validation metrics') 
                plt.legend(loc = 'best', fontsize = 8)
            plt.title('metrics plot')
            plt.ylabel('Categorical accuracy')
            plt.xlabel('epoch')       
            plt.tight_layout()
            plt.savefig(fig_path, bbox_inches = 'tight', format = 'jpeg', dpi = 300)
            plt.close()
                  
# Class for preprocessing tabular data prior to GAN training 
#==============================================================================
#==============================================================================
#==============================================================================
class PositionEmbedding(keras.layers.Layer):
    def __init__(self, sequence_length, vocab_size, output_dim, **kwargs):
        super(PositionEmbedding, self).__init__(**kwargs)
        self.word_embedding_layer = Embedding(input_dim=vocab_size, 
                                              output_dim=output_dim)
        self.position_embedding_layer = Embedding(input_dim=sequence_length, 
                                                  output_dim=output_dim)
 
    def call(self, inputs):        
        position_indices = tf.range(tf.shape(inputs)[-1])
        embedded_words = self.word_embedding_layer(inputs)
        embedded_indices = self.position_embedding_layer(position_indices)

        return embedded_words + embedded_indices

# [MACHINE LEARNING MODELS]
#==============================================================================
# collection of model and submodels
#==============================================================================
class ColorCodeModel:

    def __init__(self, learning_rate, window_size, output_size, embedding_dims, 
                 kernel_size, num_classes, seed, XLA_state):

        self.learning_rate = learning_rate
        self.window_size = window_size
        self.output_size = output_size        
        self.embedding_dims = embedding_dims
        self.kernel_size = kernel_size        
        self.num_classes = num_classes
        self.seed = seed       
        self.XLA_state = XLA_state        

    def build(self):                
        
        
        sequence_input = Input(shape=(self.window_size, 1))                   
        #----------------------------------------------------------------------
        embedding = Embedding(input_dim=self.num_classes, output_dim=self.embedding_dims)(sequence_input)        
        reshape = Reshape((self.window_size, self.embedding_dims))(embedding)       
        #---------------------------------------------------------------------- 
        conv1 = Conv1D(128, kernel_size=self.kernel_size, padding='same', activation='relu')(reshape) 
        pool1 = MaxPooling1D()(conv1)
        conv2 = Conv1D(256, kernel_size=self.kernel_size, padding='same', activation='relu')(pool1) 
        pool2 = MaxPooling1D()(conv2)
        conv3 = Conv1D(512, kernel_size=self.kernel_size, padding='same', activation='relu')(pool2)        
        #----------------------------------------------------------------------
        lstm1 = LSTM(512, use_bias=True, return_sequences=True, activation='tanh', 
                     dropout=0.2, kernel_regularizer=None)(conv3)
        lstm2 = LSTM(768, use_bias=True, return_sequences=True, activation='tanh', 
                     dropout=0.2, kernel_regularizer=None)(lstm1)             
        lstm3 = LSTM(1024, use_bias=True, return_sequences=False, activation='tanh', 
                     dropout=0.2, kernel_regularizer=None)(lstm2)         
        #----------------------------------------------------------------------        
        repeat_vector = RepeatVector(self.output_size)(lstm3) 
        #----------------------------------------------------------------------                     
        dense1 = Dense(1024, kernel_initializer='he_uniform', activation='relu')(repeat_vector)
        batchnorm1 = BatchNormalization(axis=-1, epsilon=0.001)(dense1)
        drop1 = Dropout(rate=0.2, seed=self.seed)(batchnorm1)           
        dense2 = Dense(768, kernel_initializer='he_uniform', activation='relu')(drop1)
        batchnorm2 = BatchNormalization(axis=-1, epsilon=0.001)(dense2)
        drop2 = Dropout(rate=0.2, seed=self.seed)(batchnorm2)    
        dense3 = Dense(512, kernel_initializer='he_uniform', activation='relu')(drop2)
        batchnorm3 = BatchNormalization(axis=-1, epsilon=0.001)(dense3) 
        drop3 = Dropout(rate=0.2, seed=self.seed)(batchnorm3)                             
        dense4 = Dense(256, kernel_initializer='he_uniform', activation='relu')(drop3)
        batchnorm4 = BatchNormalization(axis=-1, epsilon=0.001)(dense4)        
        drop4 = Dropout(rate=0.2, seed=self.seed)(batchnorm4)                
        dense5 = Dense(128, kernel_initializer='he_uniform', activation='relu')(drop4) 
        batchnorm5 = BatchNormalization(axis=-1, epsilon=0.001)(dense5)       
        drop5 = Dropout(rate=0.2, seed=self.seed)(batchnorm5)          
        dense6 = Dense(64, kernel_initializer='he_uniform', activation='relu')(drop5)           
        #----------------------------------------------------------------------        
        output = TimeDistributed(Dense(self.num_classes, activation='softmax', dtype='float32'))(dense6)
        #----------------------------------------------------------------------
        model = Model(inputs = sequence_input, outputs = output, name = 'CCM')    
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)
        loss = keras.losses.CategoricalCrossentropy(from_logits=False)
        metrics = keras.metrics.CategoricalAccuracy()
        model.compile(loss = loss, optimizer = opt, metrics = metrics,
                      jit_compile=self.XLA_state)       
        
        return model 

# [MACHINE LEARNING MODELS]
#==============================================================================
# collection of model and submodels
#==============================================================================
class NumMatrixModel:

    def __init__(self, learning_rate, window_size, output_size, embedding_dims,
                 kernel_size, num_classes, seed, XLA_state):

        self.learning_rate = learning_rate
        self.window_size = window_size
        self.output_size = output_size        
        self.embedding_dims = embedding_dims
        self.kernel_size = kernel_size          
        self.num_classes = num_classes
        self.seed = seed       
        self.XLA_state = XLA_state        

    def build(self):         
        
        sequence_input = Input(shape=(self.window_size, 1))
        position_input = Input(shape=(self.window_size, 1))                   
        #----------------------------------------------------------------------
        embeddingseq = Embedding(self.num_classes, self.embedding_dims)(sequence_input)               
        reshapeseq = Reshape((self.window_size, self.embedding_dims))(embeddingseq)       
        #---------------------------------------------------------------------- 
        convseq1 = Conv1D(128, kernel_size=self.kernel_size, padding='same', activation='relu')(reshapeseq) 
        poolseq1 = MaxPooling1D()(convseq1)
        convseq2 = Conv1D(256, kernel_size=self.kernel_size, padding='same', activation='relu')(poolseq1) 
        poolseq2 = MaxPooling1D()(convseq2)
        convseq3 = Conv1D(512, kernel_size=self.kernel_size, padding='same', activation='relu')(poolseq2)        
        #----------------------------------------------------------------------
        lstmseq1 = LSTM(512, use_bias=True, return_sequences=True, activation='tanh',
                        dropout=0.2, kernel_regularizer=None)(convseq3)
        lstmseq2 = LSTM(768, use_bias=True, return_sequences=True, activation='tanh', 
                        dropout=0.2, kernel_regularizer=None)(lstmseq1)             
        lstmseq3 = LSTM(1024, use_bias=True, return_sequences=False, activation='tanh', 
                        dropout=0.2, kernel_regularizer=None)(lstmseq2)                          
        #----------------------------------------------------------------------
        embeddingpos = Embedding(self.num_classes, self.embedding_dims)(position_input)              
        reshapepos = Reshape((self.window_size, self.embedding_dims))(embeddingpos)       
        #---------------------------------------------------------------------- 
        convpos1 = Conv1D(128, kernel_size=self.kernel_size, padding='same', activation='relu')(reshapepos) 
        poolpos1 = MaxPooling1D()(convpos1)
        convpos2 = Conv1D(256, kernel_size=self.kernel_size, padding='same', activation='relu')(poolpos1) 
        poolpos2 = MaxPooling1D()(convpos2)
        convpos3 = Conv1D(512, kernel_size=self.kernel_size, padding='same', activation='relu')(poolpos2)        
        #----------------------------------------------------------------------
        lstmpos1 = LSTM(512, use_bias=True, return_sequences=True, activation='tanh', 
                        dropout=0.2, kernel_regularizer=None)(convpos3) 
        lstmpos2 = LSTM(768, use_bias=True, return_sequences=True, activation='tanh',
                        dropout=0.2, kernel_regularizer=None)(lstmpos1)             
        lstmpos3 = LSTM(1024, use_bias=True, return_sequences=False, activation='tanh', 
                        dropout=0.2, kernel_regularizer=None)(lstmpos2)       
        #----------------------------------------------------------------------
        concat = Add()([lstmseq3, lstmpos3])
        densecat = Dense(1024, kernel_initializer='he_uniform', activation='relu')(concat)
        #----------------------------------------------------------------------        
        repeat_vector = RepeatVector(self.output_size)(densecat) 
        #----------------------------------------------------------------------                     
        dense1 = Dense(1024, kernel_initializer='he_uniform', activation='relu')(repeat_vector)
        batchnorm1 = BatchNormalization(axis=-1, epsilon=0.001)(dense1)
        drop1 = Dropout(rate=0.2, seed=self.seed)(batchnorm1)           
        dense2 = Dense(768, kernel_initializer='he_uniform', activation='relu')(drop1)
        batchnorm2 = BatchNormalization(axis=-1, epsilon=0.001)(dense2)
        drop2 = Dropout(rate=0.2, seed=self.seed)(batchnorm2)    
        dense3 = Dense(512, kernel_initializer='he_uniform', activation='relu')(drop2)
        batchnorm3 = BatchNormalization(axis=-1, epsilon=0.001)(dense3) 
        drop3 = Dropout(rate=0.2, seed=self.seed)(batchnorm3)                             
        dense4 = Dense(256, kernel_initializer='he_uniform', activation='relu')(drop3)
        batchnorm4 = BatchNormalization(axis=-1, epsilon=0.001)(dense4)        
        drop4 = Dropout(rate=0.2, seed=self.seed)(batchnorm4)                
        dense5 = Dense(128, kernel_initializer='he_uniform', activation='relu')(drop4) 
        batchnorm5 = BatchNormalization(axis=-1, epsilon=0.001)(dense5)       
        drop5 = Dropout(rate=0.2, seed=self.seed)(batchnorm5)          
        dense6 = Dense(64, kernel_initializer='he_uniform', activation='relu')(drop5)           
        #----------------------------------------------------------------------        
        output = TimeDistributed(Dense(self.num_classes, activation='softmax', dtype='float32'))(dense6)
        #----------------------------------------------------------------------
        model = Model(inputs = [sequence_input, position_input], outputs = output, name = 'NMM')    
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)
        loss = keras.losses.CategoricalCrossentropy(from_logits=False)
        metrics = keras.metrics.CategoricalAccuracy()
        model.compile(loss = loss, optimizer = opt, metrics = metrics,
                      jit_compile=self.XLA_state)       
        
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
          
    
    #-------------------------------------------------------------------------- 
    def load_pretrained_model(self, path, load_parameters=True):

        '''
        Load pretrained keras model (in folders) from the specified directory. 
        If multiple model directories are found, the user is prompted to select one,
        while if only one model directory is found, that model is loaded directly.
        If `load_parameters` is True, the function also loads the model parameters 
        from the target .json file in the same directory. 

        Keyword arguments:
            path (str): The directory path where the pretrained models are stored.
            load_parameters (bool, optional): If True, the function also loads the 
                                              model parameters from a JSON file. 
                                              Default is True.

        Returns:
            model (keras.Model): The loaded Keras model.

        '''        
        model_folders = []
        for entry in os.scandir(path):
            if entry.is_dir():
                model_folders.append(entry.name)
        if len(model_folders) > 1:
            model_folders.sort()
            index_list = [idx + 1 for idx, item in enumerate(model_folders)]     
            print('Please select a pretrained model:') 
            print()
            for i, directory in enumerate(model_folders):
                print(f'{i + 1} - {directory}')        
            print()               
            while True:
                try:
                    dir_index = int(input('Type the model index to select it: '))
                    print()
                except:
                    continue
                break                         
            while dir_index not in index_list:
                try:
                    dir_index = int(input('Input is not valid! Try again: '))
                    print()
                except:
                    continue
            self.model_path = os.path.join(path, model_folders[dir_index - 1])

        elif len(model_folders) == 1:
            self.model_path = os.path.join(path, model_folders[0])            
        
        model = keras.models.load_model(self.model_path)
        if load_parameters==True:
            path = os.path.join(self.model_path, 'model_parameters.json')
            with open(path, 'r') as f:
                self.model_configuration = json.load(f)            
        
        return model   


# define class for trained model validation and data comparison
#============================================================================== 
#==============================================================================
#==============================================================================
class ModelValidation:

    def __init__(self, model):      
        self.model = model       
    
    # comparison of data distribution using statistical methods 
    #==========================================================================     
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
        plot_loc = os.path.join(path, f'confusion_matrix_{name}.jpeg')
        plt.savefig(plot_loc, bbox_inches='tight', format='jpeg', dpi = dpi)

    # comparison of data distribution using statistical methods 
    #==========================================================================
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
        plt.legend(loc="lower right")       
        plot_loc = os.path.join(path, 'multi_ROC.jpeg')
        plt.savefig(plot_loc, bbox_inches='tight', format='jpeg', dpi=dpi)           
    

