# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.dataloader.generators import RouletteGenerator
from FAIRS.commons.utils.dataloader.serializer import DataSerializer, ModelSerializer
from FAIRS.commons.utils.learning.models import FAIRSnet
from FAIRS.commons.utils.learning.training import DQNTraining
from FAIRS.commons.utils.validation.reports import log_training_report
from FAIRS.commons.constants import CONFIG, DATA_PATH
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
    trainer = DQNTraining(configuration) 
    trainer.set_device()  
 

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




