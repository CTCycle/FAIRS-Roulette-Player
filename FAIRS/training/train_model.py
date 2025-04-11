# [SETTING ENVIRONMENT VARIABLES]
from FAIRS.commons.variables import EnvironmentVariables
EV = EnvironmentVariables()

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.data.serializer import DataSerializer, ModelSerializer
from FAIRS.commons.utils.learning.models import FAIRSnet
from FAIRS.commons.utils.learning.training import DQNTraining
from FAIRS.commons.utils.validation.reports import log_training_report
from FAIRS.commons.constants import CONFIG, DATA_PATH
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD DATA]
    #-------------------------------------------------------------------------- 
    dataserializer = DataSerializer(CONFIG)
    dataset, metadata = dataserializer.load_processed_data() 
    logger.info(f'Preprocessed roulette series has been loaded ({dataset.shape[0]} samples)') 
    
    # 3. [SET DEVICE]
    #-------------------------------------------------------------------------- 
    # activate DQN agent initialize training device based on given configurations    
    logger.info('Setting device for training operations')   
    trainer = DQNTraining(CONFIG, metadata) 
    trainer.set_device()   

    modelserializer = ModelSerializer()
    checkpoint_path = modelserializer.create_checkpoint_folder()   

    # build the target model and Q model based on FAIRSnet specifics
    # Q model is the main trained model, while target model is used to predict 
    # next state Q scores and is updated based on the Q model weights   
    logger.info('Building FAIRS reinforcement learning model')  
    learner = FAIRSnet(CONFIG)
    Q_model = learner.get_model(model_summary=True)
    target_model = learner.get_model(model_summary=False)    
    
    # generate graphviz plot fo the model layout         
    modelserializer.save_model_plot(Q_model, checkpoint_path)              
   
    # 3. [BUILD MODEL AND AGENT]  
    #--------------------------------------------------------------------------  
    # Setting callbacks and training routine for the machine learning model 
    # use command prompt on the model folder and (upon activating environment), 
    # use the bash command: python -m tensorboard.main --logdir tensorboard/ 
    #--------------------------------------------------------------------------
    log_training_report(dataset, CONFIG) 

    # perform training and save model at the end    
    logger.info('Start training with reinforcement learning model')
    trainer.train_model(Q_model, target_model, dataset, checkpoint_path)



