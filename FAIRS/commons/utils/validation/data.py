import os
import numpy as np
import matplotlib.pyplot as plt

from FAIRS.commons.utils.dataloader.serializer import DataSerializer
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger


# [VALIDATION OF DATA]
###############################################################################
class DataValidation:

    def __init__(self, train_data, validation_data):
        self.DPI = 400
        self.file_type = 'jpeg'
        self.train_data = train_data
        self.validation_data = validation_data
        self.serializer = DataSerializer()
        

    #--------------------------------------------------------------------------
    def get_images_for_validation(self):

        train_images = (self.serializer.load_image(pt, as_tensor=False) 
                        for pt in self.train_data)
        validation_images = (self.serializer.load_image(pt, as_tensor=False) 
                             for pt in self.validation_data)

        return {'train' : train_images, 'validation' : validation_images}

    #--------------------------------------------------------------------------
    def pixel_intensity_histogram(self):

        images = self.get_images_for_validation()
        figure_path = os.path.join(RESULTS_PATH, 'pixel_intensity_histogram.jpeg')
        plt.figure(figsize=(16, 14))        
        for name, image_set in images.items():
            pixel_intensities = np.concatenate([image.flatten() for image in image_set])
            plt.hist(pixel_intensities, bins='auto', alpha=0.5, label=name)        
        plt.title('Pixel Intensity Histograms', fontsize=16)
        plt.xlabel('Pixel Intensity', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.legend()
        plt.tight_layout()        
        plt.savefig(figure_path, bbox_inches='tight', 
                    format=self.file_type, dpi=self.DPI)
        plt.show()
        plt.close()
        

