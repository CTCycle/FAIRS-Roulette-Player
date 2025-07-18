# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.app.utils.data.serializer import DataSerializer, ModelSerializer
from FAIRS.app.utils.learning.models.qnet import FAIRSnet
from FAIRS.app.utils.learning.training.fitting import DQNTraining
from FAIRS.app.utils.validation.reports import log_training_report
from FAIRS.app.constants import CONFIG, DATA_PATH
from FAIRS.app.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD PRETRAINED MODEL]
    #--------------------------------------------------------------------------  
    # selected and load the pretrained model, then print the summary     
    logger.info('Loading specific checkpoint from pretrained models')   
    modelserializer = ModelSerializer()     
    model, configuration, metadata, checkpoint_path = modelserializer.select_and_load_checkpoint()    
    model.summary(expand_nested=True)  

    # initialize training device 
    trainer = DQNTraining(configuration) 
    trainer.set_device() 

    # 2. [LOAD DATA]
    #-------------------------------------------------------------------------- 
    dataserializer = DataSerializer(self.configuration)
    dataset, metadata = dataserializer.load_processed_data() 
    logger.info(f'Preprocessed roulette series has been loaded ({dataset.shape[0]} samples)')      
   
    # 3. [BUILD MODEL AND AGENT]  
    #--------------------------------------------------------------------------  
    # Setting callbacks and training routine for the machine learning model 
    # use command prompt on the model folder and (upon activating environment), 
    # use the bash command: python -m tensorboard.main --logdir tensorboard/ 
    #--------------------------------------------------------------------------
    log_training_report(dataset, CONFIG) 

    # perform training and save model at the end    
    logger.info('Resuming reinforcement learning from checkpoint') 
    trainer.train_model(model, model, dataset, checkpoint_path, from_checkpoint=True)




