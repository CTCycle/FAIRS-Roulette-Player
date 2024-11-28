# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.dataloader.generators import training_data_pipeline
from FAIRS.commons.utils.dataloader.serializer import DataSerializer, ModelSerializer
from FAIRS.commons.utils.learning.training import ModelTraining
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD PRETRAINED MODEL]
    #--------------------------------------------------------------------------    
    dataserializer = DataSerializer()   
    modelserializer = ModelSerializer()     
    
    # selected and load the pretrained model, then print the summary     
    logger.info('Loading specific checkpoint from pretrained models')   
    model, configuration, history = modelserializer.select_and_load_checkpoint()
    model_folder = modelserializer.loaded_model_folder
    model.summary(expand_nested=True)  
    
    # setting device for training    
    trainer = ModelTraining(configuration)    
    trainer.set_device()  

    # 2. [DEFINE IMAGES GENERATOR AND BUILD TF.DATASET]
    #--------------------------------------------------------------------------
    # initialize training device, allows changing device prior to initializing the generators
    #--------------------------------------------------------------------------   
    # load saved tf.datasets from the proper folders in the checkpoint directory     
    train_data, validation_data, metadata = dataserializer.load_preprocessed_data(model_folder)

    # initialize the TensorDataSet class with the generator instances
    # create the tf.datasets using the previously initialized generators   
    logger.info('Building data loaders') 
    train_dataset, validation_dataset = training_data_pipeline(train_data, validation_data)
    
    # 3. [TRAINING MODEL]  
    #--------------------------------------------------------------------------  
    # Setting callbacks and training routine for the features extraction model 
    # use command prompt on the model folder and (upon activating environment), 
    # use the bash command: python -m tensorboard.main --logdir tensorboard/ 
    #--------------------------------------------------------------------------
    logger.info('--------------------------------------------------------------')
    logger.info('FAIRS training report')
    logger.info('--------------------------------------------------------------')    
    logger.info(f'Number of train samples:       {train_data.shape[0]}')
    logger.info(f'Number of validation samples:  {validation_data.shape[0]}')      
    logger.info(f'Embedding dimensions:          {CONFIG["model"]["EMBEDDING_DIMS"]}')   
    logger.info(f'Batch size:                    {CONFIG["training"]["BATCH_SIZE"]}')
    logger.info(f'Epochs:                        {CONFIG["training"]["ADDITIONAL_EPOCHS"]}')
    logger.info('--------------------------------------------------------------\n')    

    # resume training from pretrained model    
    trainer.train_model(model, train_dataset, validation_dataset, model_folder,
                        from_checkpoint=True)



