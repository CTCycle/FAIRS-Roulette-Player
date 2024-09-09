# [IMPORT LIBRARIES]
import os 
import pandas as pd

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.preprocessing.mapping import RouletteMapper
from FAIRS.commons.utils.preprocessing.splitting import DatasetSplit
from FAIRS.commons.utils.preprocessing.sequences import RollingWindows
from FAIRS.commons.utils.dataloader.serializer import get_dataset, DataSerializer
from FAIRS.commons.constants import CONFIG, DATA_PATH, PP_PATH
from FAIRS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD DATA]
    #--------------------------------------------------------------------------     
    # load data from csv, add paths to images 
    logger.info(f'Loading FAIRS dataset from {DATA_PATH}')    
    df_FAIRS = get_dataset()    

    # 2. [MAP DATA TO ROULETTE POSITIONS AND COLORS]
    #--------------------------------------------------------------------------    
    mapper = RouletteMapper()
    logger.info('Encoding position and colors from raw number timeseries')    
    df_FAIRS, color_encoder = mapper.encode_roulette_extractions(df_FAIRS)
    
    # 3. [SPLIT DATASET]
    #--------------------------------------------------------------------------
    # split dataset into train and test and generate window-dataset   
    splitter = DatasetSplit(df_FAIRS)    
    train_data, validation_data = splitter.split_train_and_validation() 

    sequencer = RollingWindows() 
    train_rolling_windows = sequencer.timeseries_rolling_windows(train_data)
    val_rolling_windows = sequencer.timeseries_rolling_windows(validation_data)

    # 3. [SAVE PREPROCESSED DATA]
    #--------------------------------------------------------------------------
    # save preprocessed data using data serializer
    dataserializer = DataSerializer()
    dataserializer.save_preprocessed_data(train_rolling_windows, val_rolling_windows, PP_PATH)
    
    
   

  

    

    

