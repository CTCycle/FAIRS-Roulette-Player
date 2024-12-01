# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.process.mapping import RouletteMapper
from FAIRS.commons.utils.process.sequences import TimeSequencer
from FAIRS.commons.utils.learning.inference import RouletteGenerator
from FAIRS.commons.utils.dataloader.serializer import get_predictions_dataset, ModelSerializer
from FAIRS.commons.constants import CONFIG, PRED_PATH
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD DATA]
    #--------------------------------------------------------------------------     
    # load data from csv, add paths to images 
    logger.info(f'Loading predictions dataset from {PRED_PATH}')    
    predictions_data = get_predictions_dataset()    

    # 2. [MAP DATA TO ROULETTE POSITIONS AND COLORS]
    #--------------------------------------------------------------------------    
    mapper = RouletteMapper()
    logger.info('Encoding position and colors from raw number timeseries')    
    predictions_data, color_encoder = mapper.encode_roulette_extractions(predictions_data)
    
    # 3. [GENERATE ROLLING SEQUENCES]
    #--------------------------------------------------------------------------
    sequencer = TimeSequencer() 
    shifted_sequences = sequencer.generate_historical_sequences(predictions_data)    
      
    # 4. [LOAD MODEL]
    #--------------------------------------------------------------------------  
    # selected and load the pretrained model, then print the summary 
    # selected and load the pretrained model, then print the summary 
    modelserializer = ModelSerializer()         
    model, configuration, history, checkpoint_path = modelserializer.select_and_load_checkpoint()    
    model.summary(expand_nested=True)   
    print()     
 
    # 5. [GENERATE EXTRACTION SEQUENCES]
    #--------------------------------------------------------------------------    
    generator = RouletteGenerator(model, configuration, shifted_sequences) 
    logger.info('Generating roulette series from last window')   
    generated_timeseries = generator.generate_sequences()

    

    