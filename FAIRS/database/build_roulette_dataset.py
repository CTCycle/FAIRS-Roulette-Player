# [SETTING ENVIRONMENT VARIABLES]
from FAIRS.commons.variables import EnvironmentVariables
EV = EnvironmentVariables()

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.data.serializer import DataSerializer
from FAIRS.commons.utils.data.process.mapping import RouletteMapper
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD DATA]
    #--------------------------------------------------------------------------     
    # load data from csv, add paths to images     
    dataserializer = DataSerializer(CONFIG)
    roulette_dataset = dataserializer.load_roulette_dataset()

    # 2. [PREPROCESS DATA]
    #--------------------------------------------------------------------------
    # use the roulette generator to process raw extractions and retrieve 
    # sequence of positions and color-encoded values              
    mapper = RouletteMapper(CONFIG)
    logger.info('Encoding positional and color-based indices for roulette extractions')     
    roulette_dataset = mapper.encode_roulette_dataset(roulette_dataset)          
    
    # 3. [SAVE PREPROCESSED DATA]
    #--------------------------------------------------------------------------
    # save preprocessed data using data serializer 
    logger.info(f'Dataset includes {roulette_dataset.shape[0]} roulette extractions')     
    dataserializer.save_preprocessed_data(roulette_dataset) 

  

    

    

