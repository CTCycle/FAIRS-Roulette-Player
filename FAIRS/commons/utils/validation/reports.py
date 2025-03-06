import keras
from fpdf import FPDF

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger



###############################################################################
def evaluation_report(model : keras.Model, train_dataset, validation_dataset):
    
    train_eval = model.evaluate(train_dataset, verbose=1)
    validation_eval = model.evaluate(validation_dataset, verbose=1)
    logger.info('Train dataset:')
    logger.info(f'Loss: {train_eval[0]:.3f}')    
    logger.info(f'Metric: {train_eval[1]:.3f}')  
    logger.info('Test dataset:')
    logger.info(f'Loss: {validation_eval[0]:.3f}')    
    logger.info(f'Metric: {validation_eval[1]:.3f}')

###############################################################################
def log_training_report(train_data, config : dict):

    logger.info('--------------------------------------------------------------')
    logger.info('FAIRS training report')
    logger.info('--------------------------------------------------------------')    
    logger.info(f'Number of train samples:       {train_data.shape[0]}')    
    for key, value in config.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():                              
                if isinstance(sub_value, dict):
                    for inner_key, inner_value in sub_value.items():
                        logger.info(f'{key}.{sub_key}.{inner_key}: {inner_value}')
                else:
                    logger.info(f'{key}.{sub_key}: {sub_value}')
        else:
            logger.info(f'{key}: {value}')

    logger.info('--------------------------------------------------------------\n')

        
###############################################################################
class DataAnalysisPDF(FPDF):

    def __init__(self):
        super().__init__()        
        self.set_auto_page_break(auto=True, margin=15)

        self.introduction_text = (
            "This report summarizes the results of the image analysis.\n"
            "The statistics include mean pixel values, pixel standard deviation, and image noise ratio.\n"
            "Below, you can see the generated pixel intensity histogram.")
               
    #--------------------------------------------------------------------------
    def header(self):        
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Image Analysis Report", border=False, ln=True, align="C")
        self.ln(5)  

    #--------------------------------------------------------------------------
    def header(self): 
        self.add_page()        
        self.set_font("Arial", "", 12)
        text = ("""For every image in the dataset, we compute essential statistics 
                such as average brightness, spread of pixel values (median, standard deviation, minimum, and maximum), 
                and the range of pixel intensities. Additionally, the level of noise is estimated 
                by comparing the original image with a slightly blurred version.
                """) 
                
        self.multi_cell(0, 10, text)       
        self.set_font("Arial", "B", 16)
              
        
        
            
        
