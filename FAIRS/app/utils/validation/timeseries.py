from FAIRS.app.utils.data.serializer import DataSerializer
from FAIRS.app.constants import CONFIG
from FAIRS.app.logger import logger


# [VALIDATION OF DATA]
###############################################################################
class RouletteSeriesValidation:

    def __init__(self, configuration : dict):
        self.DPI = configuration.get('image_resolution', 400)
        self.file_type = 'jpeg'
        

    