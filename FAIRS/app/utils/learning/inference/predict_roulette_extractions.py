# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.app.utils.inference.player import RoulettePlayer
from FAIRS.app.utils.data.serializer import DataSerializer, ModelSerializer
from FAIRS.app.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD MODEL]
    #--------------------------------------------------------------------------  
    # selected and load the pretrained model, then print the summary 
    modelserializer = ModelSerializer()         
    model, configuration, checkpoint_path = modelserializer.select_and_load_checkpoint()    
    model.summary(expand_nested=True)   

    # 2. [LOAD DATA]
    #-------------------------------------------------------------------------- 
    dataserializer = DataSerializer(self.configuration)
    dataset, metadata = dataserializer.load_processed_data() 
    logger.info(f'Preprocessed roulette series has been loaded ({dataset.shape[0]} samples)') 
   
 
    # 3. [START PREDICTIONS]
    #--------------------------------------------------------------------------
    logger.info('Start predicting most rewarding actions with the selected model')    
    generator = RoulettePlayer(model, configuration)       
    roulette_predictions = generator.play_past_roulette_games(dataset)

    if CONFIG['inference']['ONLINE']:
        real_time_game = generator.play_real_time_roulette()

    

    

    