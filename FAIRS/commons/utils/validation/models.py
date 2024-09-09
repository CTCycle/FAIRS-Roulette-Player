import os
import keras
import tensorflow as tf
import matplotlib.pyplot as plt

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

    
# [BASELINE MODELS]
#============================================================================== 
# Methods for model validation
#==============================================================================
class BaselineModels:  

    def __init__(self):      
        pass   
    
    #--------------------------------------------------------------------------
    def model_accuracy(self, model, train_data, test_data):

        X_train, Y_train = train_data[0], train_data[1]  
        X_test, Y_test = test_data[0], test_data[1] 
        y_train_pred = model.predict(X_train)
        y_test_pred = model.predict(X_test)
        train_accuracy = accuracy_score(Y_train, y_train_pred)
        test_accuracy = accuracy_score(Y_test, y_test_pred) 

        return train_accuracy, test_accuracy

    #--------------------------------------------------------------------------
    def DecisionTree_classifier(self, train_data, seed=None):
        X_train, Y_train = train_data[0], train_data[1]
        model = DecisionTreeClassifier(random_state=seed)
        model.fit(X_train, Y_train)

        return model

    #--------------------------------------------------------------------------     
    def RandomForest_classifier(self, train_data, estimators, seed):
        X_train, Y_train = train_data[0], train_data[1]         
        model = RandomForestClassifier(n_estimators=estimators, random_state=seed)
        model.fit(X_train, Y_train)              

        return model
    
    
# [MODEL VALIDATION]
#============================================================================== 
# Methods for model validation
#==============================================================================
class ModelValidation:

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
        plt.show(block=False)
    
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
        plt.savefig(plot_loc, bbox_inches='tight', format='jpeg', dpi = dpi)
        plt.show(block=False)

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
        plt.show(block=False)           
    



# [VALIDATION OF PRETRAINED MODELS]
###############################################################################
class ModelValidation:

    def __init__(self, model : keras.Model):
        self.DPI = 400
        self.file_type = 'jpeg'        
        self.model = model

    #-------------------------------------------------------------------------- 
    def evaluation_report(self, train_dataset, validation_dataset):
        
        train_eval = self.model.evaluate(train_dataset, verbose=1)
        validation_eval = self.model.evaluate(validation_dataset, verbose=1)
        logger.info('Train dataset:')
        logger.info(f'Loss: {train_eval[0]}')    
        logger.info(f'Metric: {train_eval[1]}')  
        logger.info('Test dataset:')
        logger.info(f'Loss: {validation_eval[0]}')    
        logger.info(f'Metric: {validation_eval[1]}') 

    #-------------------------------------------------------------------------- 
    def visualize_features_vector(self, real_image, features, predicted_image, name, path):
        
        fig_path = os.path.join(path, f'{name}.jpeg')
        fig, axs = plt.subplots(1, 3, figsize=(14, 20), dpi=600)                                     
        axs[0].imshow(real_image)
        axs[0].set_title('Original picture')
        axs[0].axis('off')
        axs[1].imshow(features)
        axs[1].set_title('Extracted features')
        axs[1].axis('off')
        axs[2].imshow(predicted_image)
        axs[2].set_title('Reconstructed picture')
        axs[2].axis('off')
        plt.tight_layout() 
        plt.show(block=False)       
        plt.savefig(fig_path, bbox_inches='tight', format=self.file_type, dpi=self.DPI)                
        plt.close()
        
    
    #-------------------------------------------------------------------------- 
    def visualize_reconstructed_images(self, dataset : tf.data.Dataset, name, path):

        # perform visual validation for the train dataset (initialize a validation tf.dataset
        # with batch size of 10 images)
        logger.info('Visual reconstruction evaluation: train dataset')        
        batch = dataset.take(1)
        for images, labels in batch:
            recostructed_images = self.model.predict(images, verbose=0)  
            eval_path = os.path.join(path, 'data')
            num_pics = len(images)
            fig_path = os.path.join(eval_path, f'{name}.jpeg')
            fig, axs = plt.subplots(num_pics, 2, figsize=(4, num_pics * 2))
            for i, (real, pred) in enumerate(zip(images, recostructed_images)):                                                          
                axs[i, 0].imshow(real)
                if i == 0:
                    axs[i, 0].set_title('Original picture')
                axs[i, 0].axis('off')
                axs[i, 1].imshow(pred)
                if i == 0:
                    axs[i, 1].set_title('Reconstructed picture')
                axs[i, 1].axis('off')
            plt.tight_layout() 
            plt.show(block=False)       
            plt.savefig(fig_path, bbox_inches='tight', format=self.file_type, dpi=self.DPI)               
            plt.close()
        

              
        
        
            
        
