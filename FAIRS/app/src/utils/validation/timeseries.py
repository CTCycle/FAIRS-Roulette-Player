from FAIRS.app.utils.data.serializer import DataSerializer
from FAIRS.app.constants import CONFIG
from FAIRS.app.logger import logger


# [VALIDATION OF DATA]
###############################################################################
class RouletteSeriesValidation:

    def __init__(self, train_data, validation_data):
        self.DPI = 400
        self.file_type = 'jpeg'
        self.train_data = train_data
        self.validation_data = validation_data
        self.serializer = DataSerializer()
        

    