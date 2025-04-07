import os
import sqlite3
import pandas as pd

from FAIRS.commons.constants import DATA_PATH, SOURCE_PATH, INFERENCE_PATH
from FAIRS.commons.logger import logger


###############################################################################
class RouletteSeriesTable:

    def __init__(self):
        self.name = 'ROULETTE_SERIES'
        self.dtypes = {
            'timeseries': 'INTEGER'}    

    #--------------------------------------------------------------------------
    def get_dtypes(self):
        return self.dtypes
    
    #--------------------------------------------------------------------------
    def create_table(self, cursor):
        query = f'''
        CREATE TABLE IF NOT EXISTS {self.name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeseries INTEGER            
            );
            '''  
        
        cursor.execute(query) 

###############################################################################
class ProcessedDataTable:

    def __init__(self):
        self.name = 'PROCESSED_DATA'
        self.dtypes = {
            'timeseries': 'INTEGER',
            'color': 'VARCHAR',
            'color_code': 'INTEGER'}

    #--------------------------------------------------------------------------
    def get_dtypes(self):
        return self.dtypes
    
    #--------------------------------------------------------------------------
    def create_table(self, cursor):
        query = f'''
        CREATE TABLE IF NOT EXISTS {self.name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeseries INTEGER,
            color VARCHAR,
            color_code INTEGER           
        );
        '''

        cursor.execute(query)  


###############################################################################
class PredictedGameTable:

    def __init__(self):
        self.name = 'PREDICTED_GAMES'
        self.dtypes = {
            'timeseries': 'INTEGER',
            'color': 'VARCHAR',
            'color_code': 'INTEGER',
            'action': 'VARCHAR'}

    #--------------------------------------------------------------------------
    def get_dtypes(self):
        return self.dtypes
    
    #--------------------------------------------------------------------------
    def create_table(self, cursor):
        query = f'''
        CREATE TABLE IF NOT EXISTS {self.name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeseries INTEGER,
            color VARCHAR,
            color_code INTEGER,
            action VARCHAR           
        );
        '''

        cursor.execute(query) 


###############################################################################
class CheckpointSummaryTable:

    def __init__(self):
        self.name = 'CHECKPOINTS_SUMMARY'
        self.dtypes = {
            'checkpoint_name': 'VARCHAR',
            'sample_size': 'FLOAT',
            'validation_size': 'FLOAT',
            'seed': 'INTEGER',
            'precision_bits': 'INTEGER',
            'epochs': 'INTEGER',
            'additional_epochs': 'INTEGER',
            'batch_size': 'INTEGER',
            'split_seed': 'INTEGER',
            'image_augmentation': 'VARCHAR',
            'image_height': 'INTEGER',
            'image_width': 'INTEGER',
            'image_channels': 'INTEGER',
            'jit_compile': 'VARCHAR',
            'jit_backend': 'VARCHAR',
            'device': 'VARCHAR',
            'device_id': 'VARCHAR',
            'number_of_processors': 'INTEGER',
            'use_tensorboard': 'VARCHAR',
            'lr_scheduler_initial_lr': 'FLOAT',
            'lr_scheduler_constant_steps': 'FLOAT',
            'lr_scheduler_decay_steps': 'FLOAT'}    

    #--------------------------------------------------------------------------
    def get_dtypes(self):
        return self.dtypes
    
    #--------------------------------------------------------------------------
    def create_table(self, cursor):
        query = f'''
        CREATE TABLE IF NOT EXISTS {self.name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkpoint_name VARCHAR,
            sample_size FLOAT,
            validation_size FLOAT,
            seed INTEGER,
            precision_bits INTEGER,
            epochs INTEGER,
            additional_epochs INTEGER,
            batch_size INTEGER,
            split_seed INTEGER,
            image_augmentation VARCHAR,
            image_height INTEGER,
            image_width INTEGER,
            image_channels INTEGER,
            jit_compile VARCHAR,
            jit_backend VARCHAR,
            device VARCHAR,
            device_id VARCHAR,
            number_of_processors INTEGER,
            use_tensorboard VARCHAR,
            lr_scheduler_initial_lr FLOAT,
            lr_scheduler_constant_steps FLOAT,
            lr_scheduler_decay_steps FLOAT
            );
            '''  
        
        cursor.execute(query)   



# [DATABASE]
###############################################################################
class FAIRSDatabase:

    def __init__(self, configuration):             
        self.db_path = os.path.join(DATA_PATH, 'FAIRS_database.db') 
        self.source_path = os.path.join(SOURCE_PATH, 'FAIRS_dataset.csv')  
        self.inference_path = os.path.join(INFERENCE_PATH, 'FAIRS_predictions.csv')        
        self.configuration = configuration
        self.source_data = RouletteSeriesTable()
        self.processed_data = ProcessedDataTable()
        self.inference_data = PredictedGameTable()     
        self.checkpoints_summary = CheckpointSummaryTable()    
        self.initialize_database()
        self.update_database()

    #--------------------------------------------------------------------------       
    def initialize_database(self):        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        self.source_data.create_table(cursor)  
        self.processed_data.create_table(cursor)
        self.inference_data.create_table(cursor)       
        self.checkpoints_summary.create_table(cursor)   

        conn.commit()
        conn.close()

    #--------------------------------------------------------------------------
    def update_database(self):               
        source_data = pd.read_csv(self.source_path, sep=';', encoding='utf-8')      
        inference_data = pd.read_csv(self.inference_path, sep=';', encoding='utf-8')    
        self.save_source_data_table(source_data)
        self.save_inference_data_table(inference_data)

    #--------------------------------------------------------------------------
    def load_source_data_table(self):                   
        conn = sqlite3.connect(self.db_path)        
        data = pd.read_sql_query(
            f"SELECT * FROM {self.source_data.name}", conn)
        conn.close()  

        return data 

    #--------------------------------------------------------------------------
    def load_preprocessed_data_table(self):                       
        conn = sqlite3.connect(self.db_path)        
        data = pd.read_sql_query(
            f"SELECT * FROM {self.processed_data.name}", conn)
        conn.close()  

        return data      

    #--------------------------------------------------------------------------
    def save_source_data_table(self, data : pd.DataFrame):                 
        conn = sqlite3.connect(self.db_path)         
        data.to_sql(self.source_data.name, conn, if_exists='replace', index=False,
                    dtype=self.source_data.get_dtypes())
        conn.commit()
        conn.close()

    #--------------------------------------------------------------------------
    def save_preprocessed_data_table(self, data : pd.DataFrame):                
        conn = sqlite3.connect(self.db_path)         
        data.to_sql(
            self.processed_data.name, conn, if_exists='replace', index=False,
            dtype=self.processed_data.get_dtypes())
        conn.commit()
        conn.close() 

    #--------------------------------------------------------------------------
    def save_inference_data_table(self, data : pd.DataFrame):         
        conn = sqlite3.connect(self.db_path)         
        data.to_sql(
            self.inference_data.name, conn, if_exists='replace', index=False,
            dtype=self.inference_data.get_dtypes())
        conn.commit()
        conn.close()    

    #--------------------------------------------------------------------------
    def save_checkpoints_summary_table(self, data : pd.DataFrame):        
        conn = sqlite3.connect(self.db_path)         
        data.to_sql(
            self.checkpoints_summary.name, conn, if_exists='replace', index=False,
            dtype=self.checkpoints_summary.get_dtypes())
        conn.commit()
        conn.close() 

        

    