import keras

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger



###############################################################################
def evaluation_report(model : keras.Model, train_dataset, validation_dataset):
    
    train_eval = model.evaluate(train_dataset, verbose=1)
    validation_eval = model.evaluate(validation_dataset, verbose=1)
    logger.info('Train dataset:')
    logger.info(f'Loss: {train_eval[0]}')    
    logger.info(f'Metric: {train_eval[1]}')  
    logger.info('Test dataset:')
    logger.info(f'Loss: {validation_eval[0]}')    
    logger.info(f'Metric: {validation_eval[1]}')

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

        

              
        
        
            
        
