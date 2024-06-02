import os
from datetime import datetime
import numpy as np


# [PREPROCESSING]
#==============================================================================
# preprocessing tools
#==============================================================================
class PreProcessing:

    def __init__(self):
        self.position_map = {0: 0, 32: 1, 15: 2, 19: 3, 4: 4, 21: 5, 2: 6, 25: 7, 17: 8, 
                            34: 9, 6: 10, 27: 11, 13: 12, 36: 13, 11: 14, 30: 15, 8: 16, 
                            23: 17, 10: 18, 5: 19, 24: 20, 16: 21, 33: 22, 1: 23, 20: 24, 
                            14: 25, 31: 26, 9: 27, 22: 28, 18: 29, 29: 30, 7: 31, 28: 32, 
                            12: 33, 35: 34, 3: 35, 26: 36}
        self.color_map = {'black' : [15, 4, 2, 17, 6, 13, 11, 8, 10, 24, 33, 20, 31, 22, 29, 28, 35, 26],
                          'red' : [32, 19, 21, 25, 34, 27, 36, 30, 23, 5, 16, 1, 14, 9, 18, 7, 12, 3],
                          'green' : [0]}  

    #--------------------------------------------------------------------------
    def roulette_positions(self, dataframe):
        
        '''
        '''
        dataframe['position'] = dataframe['timeseries'].map(self.position_map)
        
        return dataframe
    
    
    #--------------------------------------------------------------------------
    def roulette_colormapping(self, dataframe, no_mapping=True):
        
        '''
        '''
        if no_mapping == False:                      
            reverse_color_map = {v: k for k, values in self.color_map.items() for v in values}        
            dataframe['encoding'] = dataframe['timeseries'].map(reverse_color_map)
        else:
            dataframe['encoding'] = dataframe['timeseries']

        return dataframe    
 
    #--------------------------------------------------------------------------
    def split_timeseries(self, dataframe, test_size, inverted=False):
        
        '''        
        
        Splits the input dataframe into training and testing sets based on the test size.
    
        Keyword arguments:          
            dataframe (pd.dataframe): the dataframe to be split
            test_size (float):        the proportion of data to be used as the test set
        
        Returns:            
            df_train (pd.dataframe): the training set
            df_test (pd.dataframe):  the testing set
        
        '''
        train_size = int(len(dataframe) * (1 - test_size))
        test_size = len(dataframe) - train_size 
        if inverted == True:
            df_train = dataframe.iloc[:test_size]
            df_test = dataframe.iloc[test_size:]
        else:
            df_train = dataframe.iloc[:train_size]
            df_test = dataframe.iloc[train_size:]

        return df_train, df_test   

    #--------------------------------------------------------------------------
    def timeseries_labeling(self, df, window_size, output_size=1):
        
        '''
        timeseries_labeling(dataframe, window_size)
    
        Labels time series data by splitting into input and output sequences using sliding window method.
    
        Keyword arguments:
            
        dataframe (pd.DataFrame): the time series data to be labeled
        window_size (int):        the number of time steps to use as input sequence
    
        Returns:
            
        X_array (np.ndarray):     the input sequence data
        Y_array (np.ndarray):     the output sequence data
        
        '''        
        label = np.array(df)               
        X = [label[i : i + window_size] for i in range(len(label) - window_size - output_size + 1)]
        Y = [label[i + window_size : i + window_size + output_size] for i in range(len(label) - window_size - output_size + 1)]
        
        return np.array(X), np.array(Y)
    
    
    
    
    
     
    
    
   
     
