import cv2
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PySide6.QtGui import QImage, QPixmap

from FAIRS.app.utils.data.serializer import DataSerializer, ModelSerializer
from FAIRS.app.utils.validation.timeseries import RouletteSeriesValidation
from FAIRS.app.utils.validation.checkpoints import ModelEvaluationSummary
from FAIRS.app.utils.data.mapping import RouletteMapper
from FAIRS.app.utils.learning.device import DeviceConfig
from FAIRS.app.utils.learning.models.qnet import FAIRSnet
from FAIRS.app.utils.learning.training.fitting import DQNTraining
from FAIRS.app.utils.learning.inference.player import RoulettePlayer
from FAIRS.app.interface.workers import check_thread_status, update_progress_callback

from FAIRS.app.constants import RSC_PATH
from FAIRS.app.logger import logger


###############################################################################
class GraphicsHandler:

    def __init__(self): 
        self.image_encoding = cv2.IMREAD_UNCHANGED
        self.gray_scale_encoding = cv2.IMREAD_GRAYSCALE
        self.BGRA_encoding = cv2.COLOR_BGRA2RGBA
        self.BGR_encoding = cv2.COLOR_BGR2RGB

    #--------------------------------------------------------------------------
    def convert_fig_to_qpixmap(self, fig):    
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        # get the size in pixels and initialize raw RGBA buffer
        width, height = canvas.get_width_height()        
        buf = canvas.buffer_rgba()
        # construct a QImage pointing at that memory (no PNG decoding)
        qimg = QImage(buf, width, height, QImage.Format_RGBA8888)

        return QPixmap.fromImage(qimg)
    
    #--------------------------------------------------------------------------    
    def load_image_as_pixmap(self, path):    
        img = cv2.imread(path, self.image_encoding)
        # Handle grayscale, RGB, or RGBA
        if len(img.shape) == 2:  # Grayscale
            img = cv2.cvtColor(img, self.gray_scale_encoding)
        elif img.shape[2] == 4:  # BGRA
            img = cv2.cvtColor(img, self.BGRA_encoding)
        else:  # BGR
            img = cv2.cvtColor(img, self.BGR_encoding)

        h, w = img.shape[:2]
        if img.shape[2] == 3:
            qimg = QImage(img.data, w, h, 3 * w, QImage.Format_RGB888)
        else:  
            qimg = QImage(img.data, w, h, 4 * w, QImage.Format_RGBA8888)

        return QPixmap.fromImage(qimg)


###############################################################################
class ValidationEvents:

    def __init__(self, configuration : dict):
        self.configuration = configuration  
        
    #--------------------------------------------------------------------------
    def run_dataset_evaluation_pipeline(self, metrics, progress_callback=None, worker=None):         
        serializer = DataSerializer(self.configuration)    
        sample_size = self.configuration.get("sample_size", 1.0)
        roulette_data = serializer.load_roulette_dataset(sample_size)
        logger.info(f'The loaded roulette series includes {len(roulette_data)} extractions')   
        validator = RouletteSeriesValidation(self.configuration) 

        images = []  
        if 'roulette_transitions' in metrics:
            logger.info('Current metric: roulette transitions')            

        return images 

    #--------------------------------------------------------------------------
    def get_checkpoints_summary(self, progress_callback=None, worker=None): 
        summarizer = ModelEvaluationSummary(self.configuration)    
        checkpoints_summary = summarizer.get_checkpoints_summary(progress_callback, worker) 
        logger.info(f'Checkpoints summary has been created for {checkpoints_summary.shape[0]} models')   
    
    #--------------------------------------------------------------------------
    def run_model_evaluation_pipeline(self, metrics, selected_checkpoint, progress_callback=None, worker=None):
        if selected_checkpoint is None:
            logger.warning('No checkpoint selected for resuming training')
            return
           
        logger.info(f'Loading {selected_checkpoint} checkpoint')   
        modser = ModelSerializer()       
        model, train_config, session, checkpoint_path = modser.load_checkpoint(
            selected_checkpoint)    
        model.summary(expand_nested=True)  

         # set device for training operations
        logger.info('Setting device for training operations')                
        device = DeviceConfig(self.configuration)
        device.set_device()  
        
        
        serializer = DataSerializer(self.configuration)  
        
        # check worker status to allow interruption
        check_thread_status(worker)             

        images = []
        if 'evaluation_report' in metrics:
            # evaluate model performance over the training and validation dataset 
            summarizer = ModelEvaluationSummary(self.configuration)       
            summarizer.get_evaluation_report(model, validation_dataset, worker=worker) 

        
        return images      


   

###############################################################################
class ModelEvents:

    def __init__(self, configuration : dict): 
        self.configuration = configuration 

    #--------------------------------------------------------------------------
    def get_available_checkpoints(self):
        serializer = ModelSerializer()
        return serializer.scan_checkpoints_folder()
            
    #--------------------------------------------------------------------------
    def run_training_pipeline(self, progress_callback=None, worker=None):  
        dataserializer = DataSerializer(self.configuration)
        sample_size = self.configuration.get("train_sample_size", 1.0)
        dataset = dataserializer.load_roulette_dataset(sample_size) 
        logger.info(f'Roulette series has been loaded ({len(dataset)} extractions)')        
        # use the mapper to encode extractions based on position and color              
        mapper = RouletteMapper(self.configuration)
        logger.info('Encoding roulette extractions')     
        dataset = mapper.encode_roulette_series(dataset) 
        # save update data into database    
        dataserializer.save_roulette_dataset(dataset)
        logger.info('Database updated with processed roulette series')

        # check worker status to allow interruption
        check_thread_status(worker)

        # set device for training operations        
        logger.info('Setting device for training operations') 
        device = DeviceConfig(self.configuration)   
        device.set_device() 

        # create checkpoint folder
        modser = ModelSerializer()
        checkpoint_path = modser.create_checkpoint_folder()
        # build the target model and Q model based on FAIRSnet specifics
        # Q model is the main trained model, while target model is used to predict 
        # next state Q scores and is updated based on the Q model weights   
        logger.info('Building FAIRS reinforcement learning model')  
        learner = FAIRSnet(self.configuration)
        Q_model = learner.get_model(model_summary=True)
        target_model = learner.get_model(model_summary=False) 
        # generate graphviz plot fo the model layout         
        modser.save_model_plot(Q_model, checkpoint_path)          

        # perform training and save model at the end       
        trainer = DQNTraining(self.configuration)
        logger.info('Start training with reinforcement learning model')
        trainer.train_model(
            Q_model, target_model, dataset, checkpoint_path,
            progress_callback=progress_callback, worker=worker)
        
    #--------------------------------------------------------------------------
    def resume_training_pipeline(self, selected_checkpoint, progress_callback=None, 
                                 worker=None):
        if selected_checkpoint is None:
            logger.warning('No checkpoint selected for resuming training')
            return
        
        logger.info(f'Loading {selected_checkpoint} checkpoint') 
        modser = ModelSerializer()         
        model, train_config, session, checkpoint_path = modser.load_checkpoint(
            selected_checkpoint)    
        model.summary(expand_nested=True)  
        
        # set device for training operations
        logger.info('Setting device for training operations')                 
        device = DeviceConfig(self.configuration) 
        device.set_device()

        # process dataset using model configurations
        dataserializer = DataSerializer(self.configuration)
        sample_size = train_config.get("train_sample_size", 1.0)
        dataset = dataserializer.load_roulette_dataset() 
        logger.info(f'Roulette series has been loaded ({len(dataset)} extractions)')        
        # use the mapper to encode extractions based on position and color              
        mapper = RouletteMapper(train_config)
        logger.info('Encoding roulette extractions')     
        dataset = mapper.encode_roulette_series(dataset) 

        # check worker status to allow interruption
        check_thread_status(worker)         
                            
        # perform training and save model at the end       
        trainer = DQNTraining(train_config)
        logger.info('Start training with reinforcement learning model')
        additional_epochs = self.configuration.get('additional_episodes', 10)
        trainer.resume_training(
            model, model, dataset, checkpoint_path, session,
            additional_epochs, progress_callback=progress_callback, worker=worker)
        
    #--------------------------------------------------------------------------
    def run_inference_pipeline(self, selected_checkpoint, progress_callback=None, worker=None):
        logger.info(f'Loading {selected_checkpoint} checkpoint') 
        modser = ModelSerializer()         
        model, train_config, session, checkpoint_path = modser.load_checkpoint(
            selected_checkpoint)    
        model.summary(expand_nested=True)   

        # set device for training operations
        logger.info('Setting device for training operations')                 
        device = DeviceConfig(self.configuration) 
        device.set_device()

        # process dataset using model configurations
        dataserializer = DataSerializer(self.configuration)
        sample_size = train_config.get("train_sample_size", 1.0)
        dataset = dataserializer.load_roulette_dataset() 
        logger.info(f'Roulette series has been loaded ({len(dataset)} extractions)')        
        # use the mapper to encode extractions based on position and color              
        mapper = RouletteMapper(train_config)
        logger.info('Encoding roulette extractions')     
        dataset = mapper.encode_roulette_series(dataset) 
       
        logger.info('Start predicting most rewarding actions with the selected model')    
        generator = RoulettePlayer(model, train_config)       
        roulette_predictions = generator.play_past_roulette_games(
            dataset, progress_callback=progress_callback, worker=worker)
        

        if CONFIG['inference']['ONLINE']:
            real_time_game = generator.play_real_time_roulette()


