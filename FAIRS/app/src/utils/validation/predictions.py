import os
import numpy as np
import keras
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

from FAIRS.app.src.constants import CONFIG
from FAIRS.app.src.logger import logger    



# [VALIDATION OF PRETRAINED MODELS]
###############################################################################
class BetsAccuracy:

    def __init__(self, model : keras.Model):
        self.DPI = 400
        self.file_type = 'jpeg'        
        self.model = model  

    # comparison of data distribution using statistical methods 
    #--------------------------------------------------------------------------     
    def plot_timeseries_prediction(self, values, name, path, dpi=400):
        train_data = values['train']
        test_data = values['test']
        plt.figure(figsize=(12, 10))        
        plt.scatter(train_data[0], train_data[1], label='True train', color='blue')
        plt.scatter(test_data[0], test_data[1], label='True test', color='cyan')        
        plt.scatter(train_data[0], train_data[2], label='Predicted train', color='orange')
        plt.scatter(test_data[0], test_data[2], label='Predicted test', color='magenta')
        plt.xlabel('Extraction N.', fontsize=14)
        plt.ylabel('Class', fontsize=14)
        plt.title('FAIRS Extractions', fontsize=14)
        plt.legend()
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plot_loc = os.path.join(path, f'{name}.jpeg')
        plt.savefig(plot_loc, bbox_inches='tight', format='jpeg', dpi=dpi)
        plt.close()
    
    # comparison of data distribution using statistical methods 
    #--------------------------------------------------------------------------     
    def plot_confusion_matrix(self, Y_real, predictions, name, path, dpi=400): 
        class_names = ['green', 'black', 'red']        
        cm = confusion_matrix(Y_real, predictions)    
        plt.figure(figsize=(14, 14))        
        sns.heatmap(cm, annot=True, fmt='d', cmap=plt.cm.Blues, cbar=False)        
        plt.xlabel('Predicted labels', fontsize=14)
        plt.ylabel('True labels', fontsize=14)
        plt.title('Confusion Matrix', fontsize=14)
        plt.xticks(np.arange(len(class_names)) + 0.5, class_names, rotation=45, fontsize=12, ha="right")
        plt.yticks(np.arange(len(class_names)) + 0.5, class_names, rotation=0, fontsize=12, va="center")          
        plt.tight_layout()
        plot_loc = os.path.join(path, f'{name}.jpeg')
        plt.savefig(plot_loc, bbox_inches='tight', format='jpeg', dpi=self.DPI)
        plt.close()

    
        

              
        
        
            
        
