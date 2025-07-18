# [SETTING ENVIRONMENT VARIABLES]
from FAIRS.app.variables import EnvironmentVariables
EV = EnvironmentVariables()

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.app.utils.data.serializer import DataSerializer
from FAIRS.app.utils.validation.timeseries import RouletteSeriesValidation
from FAIRS.app.constants import CONFIG
from FAIRS.app.logger import logger

# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD DATASET]
    #--------------------------------------------------------------------------  
    serializer = DataSerializer(CONFIG)     
    images_paths = serializer.get_images_path_from_directory(IMG_PATH)  
    logger.info(f'The image dataset is composed of {len(images_paths)} images')  
