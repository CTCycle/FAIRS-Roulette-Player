import os
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from tensorflow import keras
from keras.models import Model
from keras.layers import Dense, Dropout, LSTM, Conv1D, BatchNormalization, Flatten, AveragePooling1D
from keras.layers import Embedding, Reshape, Input, RepeatVector, TimeDistributed, Concatenate
from sklearn.metrics import confusion_matrix, roc_curve, auc
from sklearn.preprocessing import label_binarize


# [CALLBACK FOR REAL TIME TRAINING MONITORING]
#==============================================================================
#==============================================================================
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
        if epoch % 50 == 0:            
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
class ColorCodeModel:

    def __init__(self, learning_rate, window_size, output_size, neurons, embedding_dims, 
                 kernel_size, num_classes, seed, XLA_state):

        self.learning_rate = learning_rate
        self.window_size = window_size
        self.output_size = output_size
        self.neurons = neurons
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
        lstm1 = LSTM(self.neurons, use_bias=True, return_sequences=True, activation='tanh', dropout=0.2)(reshape)         
        lstm2 = LSTM(self.neurons*2, use_bias=True, return_sequences=True, activation='tanh', dropout=0.2)(lstm1)        
        lstm3 = LSTM(self.neurons*4, use_bias=True, return_sequences=False, activation='tanh', dropout=0.2)(lstm2) 
        delstm = Dense(self.neurons*4, kernel_initializer='he_uniform', activation='relu')(lstm3)
        #----------------------------------------------------------------------         
        conv1 = Conv1D(self.neurons, kernel_size=6, padding='same', kernel_initializer='he_uniform', activation='relu')(reshape) 
        pool1 = AveragePooling1D(pool_size=2, padding='same')(conv1)        
        conv2 = Conv1D(self.neurons*2, kernel_size=6, padding='same', kernel_initializer='he_uniform', activation='relu')(pool1) 
        pool2 = AveragePooling1D(pool_size=2, padding='same')(conv2)          
        conv3 = Conv1D(self.neurons*3, kernel_size=6, padding='same', kernel_initializer='he_uniform', activation='relu')(pool2)
        pool3 = AveragePooling1D(pool_size=2, padding='same')(conv3) 
        flatten = Flatten()(pool3)   
        #---------------------------------------------------------------------- 
        concat = Concatenate()([delstm, flatten]) 
        #----------------------------------------------------------------------        
        repeat_vector = RepeatVector(self.output_size)(concat)                      
        dense1 = Dense(self.neurons*6, kernel_initializer='he_uniform', activation='relu')(repeat_vector)
        batchnorm1 = BatchNormalization()(dense1)
        drop1 = Dropout(rate=0.2, seed=self.seed)(batchnorm1)           
        dense2 = Dense(self.neurons*5, kernel_initializer='he_uniform', activation='relu')(drop1)
        batchnorm2 = BatchNormalization()(dense2)
        drop2 = Dropout(rate=0.2, seed=self.seed)(batchnorm2)    
        dense3 = Dense(self.neurons*4, kernel_initializer='he_uniform', activation='relu')(drop2)
        batchnorm3 = BatchNormalization()(dense3) 
        drop3 = Dropout(rate=0.2, seed=self.seed)(batchnorm3)                             
        dense4 = Dense(self.neurons*3, kernel_initializer='he_uniform', activation='relu')(drop3)
        batchnorm4 = BatchNormalization()(dense4)        
        drop4 = Dropout(rate=0.2, seed=self.seed)(batchnorm4)                
        dense5 = Dense(self.neurons*2, kernel_initializer='he_uniform', activation='relu')(drop4) 
        batchnorm5 = BatchNormalization()(dense5)       
        drop5 = Dropout(rate=0.2, seed=self.seed)(batchnorm5)          
        dense6 = Dense(self.neurons, kernel_initializer='he_uniform', activation='relu')(drop5)           
        #----------------------------------------------------------------------        
        output = TimeDistributed(Dense(self.num_classes, activation='softmax', dtype='float32'))(dense6)

        model = Model(inputs = sequence_input, outputs = output, name = 'FAIRS_model')    
        opt = keras.optimizers.Adam(learning_rate=self.learning_rate)
        loss = keras.losses.CategoricalCrossentropy(from_logits=False)
        metrics = keras.metrics.CategoricalAccuracy()
        model.compile(loss = loss, optimizer = opt, metrics = metrics,
                      jit_compile=self.XLA_state)       
        
        return model             


# define model class
#==============================================================================
#==============================================================================
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
    
    #========================================================================== 
    def model_parameters(self, parameters_dict, savepath): 
        path = os.path.join(savepath, 'model_parameters.json')      
        with open(path, 'w') as f:
            json.dump(parameters_dict, f) 
          
    # sequential model as generator with Keras module
    #========================================================================== 
    def load_pretrained_model(self, path, load_parameters=True):
        
        model_folders = []
        for entry in os.scandir(path):
            if entry.is_dir():
                model_folders.append(entry.name)
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
           
        model_path = os.path.join(path, model_folders[dir_index - 1])
        model = keras.models.load_model(model_path)
        if load_parameters==True:
            path = os.path.join(model_path, 'model_parameters.json')
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
        ax.xaxis.set_ticklabels(Y_real)
        ax.yaxis.set_ticklabels(predictions)
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
    

