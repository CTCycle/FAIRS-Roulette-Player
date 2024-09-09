# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.dataloader.generators import training_data_pipeline
from FAIRS.commons.utils.dataloader.serializer import get_images_path, DataSerializer, ModelSerializer
from FAIRS.commons.utils.preprocessing import DataSplit
from FAIRS.commons.utils.learning.training import ModelTraining
from FAIRS.commons.utils.learning.autoencoder import FeXTAutoEncoder
from FAIRS.commons.constants import CONFIG, IMG_DATA_PATH
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD AND SPLIT DATA]
    #--------------------------------------------------------------------------    
    # select a fraction of data for training 
    sample_size = CONFIG["dataset"]["SAMPLE_SIZE"]   
    images_paths = get_images_path(IMG_DATA_PATH, sample_size=sample_size)    

    # split data into train and validation        
    logger.info('Preparing dataset of images based on splitting sizes')  
    splitter = DataSplit(images_paths)     
    train_data, validation_data = splitter.split_train_and_validation()   

    # create subfolder for preprocessing data    
    logger.info('Saving images path references') 
    dataserializer = DataSerializer()
    modelserializer = ModelSerializer()
    model_folder_path = modelserializer.create_checkpoint_folder() 

    # save preprocessed data references
    dataserializer.save_preprocessed_data(train_data, validation_data, 
                                          model_folder_path)    

    # 2. [DEFINE IMAGES GENERATOR AND BUILD TF.DATASET]
    #--------------------------------------------------------------------------
    # initialize training device, allows changing device prior to initializing the generators
    #--------------------------------------------------------------------------
    logger.info('Building autoencoder model and data loaders')     
    trainer = ModelTraining(CONFIG)    

    # initialize the TensorDataSet class with the generator instances
    # create the tf.datasets using the previously initialized generators    
    train_dataset, validation_dataset = training_data_pipeline(train_data, validation_data)         
    
    # 3. [TRAINING MODEL]  
    #--------------------------------------------------------------------------  
    # Setting callbacks and training routine for the features extraction model 
    # use command prompt on the model folder and (upon activating environment), 
    # use the bash command: python -m tensorboard.main --logdir tensorboard/ 
    #--------------------------------------------------------------------------
    logger.info('--------------------------------------------------------------')
    logger.info('FeXT training report')
    logger.info('--------------------------------------------------------------')    
    logger.info(f'Number of train samples:       {len(train_data)}')
    logger.info(f'Number of validation samples:  {len(validation_data)}')      
    logger.info(f'Picture shape:                 {CONFIG["model"]["IMG_SHAPE"]}')   
    logger.info(f'Batch size:                    {CONFIG["training"]["BATCH_SIZE"]}')
    logger.info(f'Epochs:                        {CONFIG["training"]["EPOCHS"]}')  
    logger.info('--------------------------------------------------------------\n')  

    # build the autoencoder model     
    autoencoder = FeXTAutoEncoder()
    model = autoencoder.get_model(summary=True)
    
    # generate graphviz plot fo the model layout         
    modelserializer.save_model_plot(model, model_folder_path)              

    # perform training and save model at the end
    trainer.train_model(model, train_dataset, validation_dataset, model_folder_path)



