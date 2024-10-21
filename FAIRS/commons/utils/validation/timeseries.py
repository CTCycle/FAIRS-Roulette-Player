import os
import numpy as np
import matplotlib.pyplot as plt

from FAIRS.commons.utils.dataloader.serializer import DataSerializer
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger


# [VALIDATION OF DATA]
###############################################################################
class RouletteDataValidation:

    def __init__(self, train_data, validation_data):
        self.DPI = 400
        self.file_type = 'jpeg'
        self.train_data = train_data
        self.validation_data = validation_data
        self.serializer = DataSerializer()
        

    