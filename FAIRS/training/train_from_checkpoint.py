# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.learning.training import DQNTraining
from FAIRS.commons.utils.dataloader.generators import ML_model_dataloader
from FAIRS.commons.utils.dataloader.serializer import DataSerializer, ModelSerializer
from FAIRS.commons.utils.learning.training import ModelTraining
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD PRETRAINED MODEL]
    #--------------------------------------------------------------------------    
    
   
    # selected and load the pretrained model, then print the summary     
    logger.info('Loading specific checkpoint from pretrained models')   
    modelserializer = ModelSerializer()     
    model, configuration, history, checkpoint_path = modelserializer.select_and_load_checkpoint()    
    model.summary(expand_nested=True)  
    
    # 2. [BUILD MODEL AND AGENTSL]  
    #-------------------------------------------------------------------------- 
    # initialize training device 
    # allows changing device prior to initializing the generators    
    trainer = DQNTraining(configuration) 
    trainer.set_device()  

    # 2. [DEFINE IMAGES GENERATOR AND BUILD TF.DATASET]
    #--------------------------------------------------------------------------
    # initialize training device, allows changing device prior to initializing the generators
    #--------------------------------------------------------------------------   
    # load saved tf.datasets from the proper folders in the checkpoint directory  
    logger.info('Loading preprocessed data and building dataloaders')
    pp_data_path = os.path.join(checkpoint_path, 'data') 
    dataserializer = DataSerializer()      
    train_data, validation_data, metadata = dataserializer.load_preprocessed_data(checkpoint_path)

    # initialize the TensorDataSet class with the generator instances
    # create the tf.datasets using the previously initialized generators   
    logger.info('Building data loaders') 
    train_dataset, validation_dataset = ML_model_dataloader(train_data, validation_data)
    
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
    trainer.train_model(model, train_dataset, validation_dataset, checkpoint_path,
                        from_checkpoint=True)


    # 1. [LOAD DATA]
    #--------------------------------------------------------------------------     
    # load data from csv, add paths to images 
    logger.info(f'Loading FAIRS dataset from {DATA_PATH}')     
    generator = RouletteGenerator(CONFIG)    
    roulette_dataset, color_encoder = generator.prepare_roulette_dataset()
    
    # 2. [BUILD MODEL AND AGENTSL]  
    #-------------------------------------------------------------------------- 
    # initialize training device 
    # allows changing device prior to initializing the generators
    logger.info('Building FAIRS model and data loaders')     
    trainer = DQNTraining(CONFIG) 
    trainer.set_device()    
       
    # create subfolder for saving the checkpoint    
    modelserializer = ModelSerializer()
    checkpoint_path = modelserializer.create_checkpoint_folder()  

    # build the FAIRSnet model and the DQNA agent     
    learner = FAIRSnet(CONFIG)
    Q_model = learner.get_model(model_summary=True)
    target_model = learner.get_model(model_summary=False)    
    
    # generate graphviz plot fo the model layout         
    modelserializer.save_model_plot(Q_model, checkpoint_path)              
   
    # 3. [BUILD MODEL AND AGENT]  
    #--------------------------------------------------------------------------  
    # Setting callbacks and training routine for the features extraction model 
    # use command prompt on the model folder and (upon activating environment), 
    # use the bash command: python -m tensorboard.main --logdir tensorboard/ 
    #--------------------------------------------------------------------------
    log_training_report(roulette_dataset, CONFIG) 

    # perform training and save model at the end    
    logger.info('Start training with reinforcement learning routine')
    trainer.train_model(Q_model, target_model, roulette_dataset, checkpoint_path)




