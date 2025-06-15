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
    dataserializer = DataSerializer(self.configuration)
    dataset = dataserializer.load_roulette_dataset()
    logger.info(f'Roulette series has been loaded ({dataset.shape[0]} extractions)')

    # 2. [PREPROCESS DATA]
    #--------------------------------------------------------------------------
    # use the roulette generator to process raw extractions and retrieve 
    # sequence of positions and color-encoded values              
    mapper = RouletteMapper(self.configuration)
    logger.info('Encoding roulette extractions based on positions and colors')     
    dataset = mapper.encode_roulette_dataset(dataset)          
    
    # 3. [SAVE PREPROCESSED DATA]
    #--------------------------------------------------------------------------      
    dataserializer.save_preprocessed_data(dataset)
    logger.info('Preprocessed data saved into FAIRS database')  

  

    

    

