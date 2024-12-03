# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.dataloader.generators import RouletteGenerator
from FAIRS.commons.utils.learning.inference import RoulettePlayer
from FAIRS.commons.utils.dataloader.serializer import ModelSerializer
from FAIRS.commons.constants import CONFIG, PRED_PATH
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD MODEL]
    #--------------------------------------------------------------------------  
    # selected and load the pretrained model, then print the summary 
    modelserializer = ModelSerializer()         
    model, configuration, history, checkpoint_path = modelserializer.select_and_load_checkpoint()    
    model.summary(expand_nested=True)   
    print()       
   
    # 1. [LOAD DATA]
    #-------------------------------------------------------------------------- 
    generator = RouletteGenerator(CONFIG)    
    roulette_dataset, color_encoder = generator.prepare_roulette_dataset() 
 
    # 2. [GENERATE EXTRACTION SEQUENCES]
    #--------------------------------------------------------------------------    
    generator = RoulettePlayer(model, configuration) 
    logger.info('Generating roulette series from last window')   
    generated_timeseries = generator.generate_sequences()

    

    