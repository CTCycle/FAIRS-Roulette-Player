# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.inference.player import RoulettePlayer, save_predictions_to_csv
from FAIRS.commons.utils.data.serializer import ModelSerializer
from FAIRS.commons.constants import CONFIG
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
    # load the timeseries for predictions and use the roulette generator to process 
    # raw extractions and retrieve sequence of positions and color-encoded values  
    generator = RouletteGenerator(configuration)    
    dataset_path = os.path.join(PRED_PATH, 'FAIRS_predictions.csv')
    prediction_dataset = generator.prepare_roulette_dataset(dataset_path) 
 
    # 2. [START PREDICTIONS]
    #--------------------------------------------------------------------------
    logger.info('Start predicting most rewarding actions with the selected model')    
    generator = RoulettePlayer(model, configuration)       
    roulette_predictions = generator.play_past_roulette_games(prediction_dataset)

    if CONFIG['inference']['ONLINE']:
        real_time_game = generator.play_real_time_roulette()

    # save predictions as .csv file in the predictions folder
    save_predictions_to_csv(roulette_predictions, os.path.basename(checkpoint_path))

    

    