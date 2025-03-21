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
    # use the roulette generator to process raw extractions and retrieve 
    # sequence of positions and color-encoded values        
    logger.info(f'Loading FAIRS dataset from {DATA_PATH}')           
    generator = RouletteGenerator(CONFIG)     
    roulette_dataset = generator.prepare_roulette_dataset(dataset_path)    
    
    # 2. [BUILD MODEL AND AGENTS]  
    #-------------------------------------------------------------------------- 
    # activate DQN agent initialize training device based on given configurations    
    logger.info('Building FAIRS model and data loaders')     
    trainer = DQNTraining(CONFIG) 
    trainer.set_device()    
       
    # create folder for saving the new checkpoint    
    modelserializer = ModelSerializer()
    checkpoint_path = modelserializer.create_checkpoint_folder()  
    logger.info(f'Saving roulette extraction data in {checkpoint_path}')

    # save preprocessed roulette data into the checkpoint folder
    dataserializer = DataSerializer(CONFIG)
    dataserializer.save_preprocessed_data(roulette_dataset, checkpoint_path)  

    # build the target model and Q model based on FAIRSnet specifics
    # Q model is the main trained model, while target model is used to predict 
    # next state Q scores and is updated based on the Q model weights     
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
    logger.info('Start training with reinforcement learning pipeline')
    trainer.train_model(Q_model, target_model, roulette_dataset, checkpoint_path)



