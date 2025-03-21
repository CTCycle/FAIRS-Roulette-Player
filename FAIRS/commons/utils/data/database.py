import os
import sqlite3
import pandas as pd

from FAIRS.commons.constants import DATA_PATH
from FAIRS.commons.logger import logger

# [DATABASE]
###############################################################################
class FAIRSDatabase:

    def __init__(self, configuration):             
        self.db_path = os.path.join(DATA_PATH, 'FAIRS_database.db')         
        self.configuration = configuration

    #--------------------------------------------------------------------------
    def load_roulette_series(self): 
        # Connect to the database and select roulette series data table               
        conn = sqlite3.connect(self.db_path)        
        data = pd.read_sql_query(f"SELECT * FROM ROULETTE_DATASET", conn)
        conn.close()  

        return data 

    #--------------------------------------------------------------------------
    def load_preprocessed_roulette_series(self, data : pd.DataFrame): 
        # Connect to the database and select roulette series data table               
        conn = sqlite3.connect(self.db_path)        
        data = pd.read_sql_query(f"SELECT * FROM PROCESSED_ROULETTE_DATASET", conn)
        conn.close()  

        return data      

    #--------------------------------------------------------------------------
    def save_roulette_series(self, data : pd.DataFrame): 
        # connect to sqlite database and save the roulette series as table
        conn = sqlite3.connect(self.db_path)         
        data.to_sql('ROULETTE_DATASET', conn, if_exists='replace')
        conn.commit()
        conn.close()

    #--------------------------------------------------------------------------
    def save_preprocessed_roulette_series(self, data : pd.DataFrame): 
        # connect to sqlite database and save the roulette series as table
        conn = sqlite3.connect(self.db_path)         
        data.to_sql('PROCESSED_ROULETTE_DATASET', conn, if_exists='replace')
        conn.commit()
        conn.close()    

    #--------------------------------------------------------------------------
    def save_checkpoints_summary(self, data : pd.DataFrame): 
        # connect to sqlite database and save the preprocessed data as table
        conn = sqlite3.connect(self.db_path)         
        data.to_sql('CHECKPOINTS_SUMMARY', conn, if_exists='replace')
        conn.commit()
        conn.close() 
        

    