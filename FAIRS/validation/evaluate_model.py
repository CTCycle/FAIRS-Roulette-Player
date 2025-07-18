# [SETTING ENVIRONMENT VARIABLES]
from FAIRS.app.variables import EnvironmentVariables
EV = EnvironmentVariables()

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.app.utils.data.serializer import DataSerializer, ModelSerializer
from FAIRS.app.utils.validation.reports import evaluation_report
from FAIRS.app.utils.validation.checkpoints import ModelEvaluationSummary
from FAIRS.app.constants import CONFIG
from FAIRS.app.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':    

    # 1. [LOAD DATASET]
    #--------------------------------------------------------------------------  
    summarizer = ModelEvaluationSummary()    
    checkpoints_summary = summarizer.checkpoints_summary() 
    logger.info(f'Checkpoints summary has been created for {checkpoints_summary.shape[0]} models')  
    
    # 2. [LOAD MODEL]
    #--------------------------------------------------------------------------
    # selected and load the pretrained model, then print the summary 
    modelserializer = ModelSerializer()         
    model, configuration, checkpoint_path = modelserializer.select_and_load_checkpoint()
    model.summary(expand_nested=True)   
   
   