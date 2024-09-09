# [SET KERAS BACKEND]
import os 
import pandas as pd
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.preprocessing.mapping import RouletteMapper
from FAIRS.commons.utils.preprocessing.splitting import DatasetSplit
from FAIRS.commons.utils.preprocessing.sequences import RollingWindows
from FAIRS.commons.utils.dataloader.generators import training_data_pipeline
from FAIRS.commons.utils.dataloader.serializer import get_dataset, DataSerializer, ModelSerializer
from FAIRS.commons.utils.learning.models import FAIRSnet
from FAIRS.commons.utils.learning.training import ModelTraining
from FAIRS.commons.constants import CONFIG, DATA_PATH, DATASET_NAME
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD DATA]
    #--------------------------------------------------------------------------     
    # load data from csv, add paths to images 
    logger.info(f'Loading FAIRS dataset from {DATA_PATH}')    
    df_FAIRS = get_dataset()    

    # 2. [MAP DATA TO ROULETTE POSITIONS AND COLORS]
    #--------------------------------------------------------------------------    
    mapper = RouletteMapper()
    logger.info('Encoding position and colors from raw number timeseries')    
    df_FAIRS, color_encoder = mapper.encode_roulette_extractions(df_FAIRS)
    
    # 3. [SPLIT DATASET]
    #--------------------------------------------------------------------------
    # split dataset into train and test and generate window-dataset   
    splitter = DatasetSplit(df_FAIRS)    
    train_data, validation_data = splitter.split_train_and_validation() 

    sequencer = RollingWindows() 
    train_rolling_windows = sequencer.timeseries_rolling_windows(train_data)
    val_rolling_windows = sequencer.timeseries_rolling_windows(validation_data)
    train_X, val_X, train_Y, val_Y = sequencer.stack_features_by_window(train_rolling_windows, 
                                                                        val_rolling_windows)    

    # 3. [SAVE PREPROCESSED DATA]
    #--------------------------------------------------------------------------
    # create subfolder for preprocessing data    
    modelserializer = ModelSerializer()
    model_folder_path = modelserializer.create_checkpoint_folder()  

    # save preprocessed data using data serializer
    dataserializer = DataSerializer()
    processed_data_path = os.path.join(model_folder_path, 'data')   
    dataserializer.save_preprocessed_data(train_X, val_X, train_Y, val_Y, processed_data_path)   
      

    # 4. [DEFINE GENERATOR AND BUILD TF.DATASET]
    #--------------------------------------------------------------------------
    # initialize training device 
    # allows changing device prior to initializing the generators
    logger.info('Building FAIRS model and data loaders')     
    trainer = ModelTraining(CONFIG) 
    trainer.set_device()    
       
    # create the tf.datasets using the previously initialized generators    
    train_dataset, validation_dataset = training_data_pipeline(train_X, train_Y, 
                                                               val_X, val_Y)   
   
    # 3. [TRAINING MODEL]  
    #--------------------------------------------------------------------------  
    # Setting callbacks and training routine for the features extraction model 
    # use command prompt on the model folder and (upon activating environment), 
    # use the bash command: python -m tensorboard.main --logdir tensorboard/ 
    #--------------------------------------------------------------------------
    logger.info('--------------------------------------------------------------')
    logger.info('FAIRS training report')
    logger.info('--------------------------------------------------------------')    
    logger.info(f'Number of train samples:       {len(train_data)}')
    logger.info(f'Number of validation samples:  {len(validation_data)}')      
    logger.info(f'Embedding dimensions:          {CONFIG["model"]["EMBEDDING_DIMS"]}')   
    logger.info(f'Batch size:                    {CONFIG["training"]["BATCH_SIZE"]}')
    logger.info(f'Epochs:                        {CONFIG["training"]["EPOCHS"]}')  
    logger.info('--------------------------------------------------------------\n')  

    # build the autoencoder model     
    classifier = FAIRSnet()
    model = classifier.get_model(summary=True)
    
    # generate graphviz plot fo the model layout         
    modelserializer.save_model_plot(model, model_folder_path)              

    # perform training and save model at the end
    trainer.train_model(model, train_dataset, validation_dataset, model_folder_path)



