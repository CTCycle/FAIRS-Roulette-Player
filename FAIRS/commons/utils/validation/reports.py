import keras

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger


###############################################################################
def evaluation_report(model : keras.Model, train_dataset, validation_dataset):    
    training = model.evaluate(train_dataset, verbose=1)
    validation = model.evaluate(validation_dataset, verbose=1)
    logger.info(
        f'Training loss {training[0]:.3f} - Training metric {training[1]:.3f}')    
    logger.info(
        f'Validation loss {validation[0]:.3f} - Validation metric {validation[1]:.3f}') 
     

###############################################################################
def log_training_report(train_data, config : dict):
    logger.info('--------------------------------------------------------------')
    logger.info('FAIRS training report')
    logger.info('--------------------------------------------------------------')    
    logger.info(f'Number of train samples:       {train_data.shape[0]}')    
    for key, value in config.items():
        if isinstance(value, dict) and ('validation' not in key and 'inference' not in key):
            for sub_key, sub_value in value.items():                              
                if isinstance(sub_value, dict):
                    for inner_key, inner_value in sub_value.items():
                        logger.info(f'{key}.{sub_key}.{inner_key}: {inner_value}')
                else:
                    logger.info(f'{key}.{sub_key}: {sub_value}')
        elif 'validation' not in key and 'inference' not in key:
            logger.info(f'{key}: {value}')

    logger.info('--------------------------------------------------------------\n')

        
