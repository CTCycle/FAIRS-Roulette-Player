import os
from datetime import datetime
import numpy as np


# ...
#==============================================================================
#==============================================================================
#==============================================================================
class UserOperations:
    
    """    
    A class for user operations such as interactions with the console, directories 
    and files cleaning and other maintenance operations.
      
    Methods:
        
    menu_selection(menu):         console menu management
    clear_all_files(folder_path): cleaning files and directories 
   
    """
    
    #==========================================================================
    def menu_selection(self, menu):
        
        """        
        menu_selection(menu)
        
        Presents a menu to the user and returns the selected option.
        
        Keyword arguments:                      
            menu (dict): A dictionary containing the options to be presented to the user. 
                         The keys are integers representing the option numbers, and the 
                         values are strings representing the option descriptions.
        
        Returns:            
            op_sel (int): The selected option number.
        
        """
        
        indexes = [idx + 1 for idx, val in enumerate(menu)]
        for key, value in menu.items():
            print('{0} - {1}'.format(key, value))       
        print()
        while True:
            try:
                op_sel = int(input('Select the desired operation: '))
            except:
                continue           
            while op_sel not in indexes:
                try:
                    op_sel = int(input('Input is not valid, please select a valid option: '))
                except:
                    continue
            break
        
        return op_sel
    
    
               
    #==========================================================================
    def datetime_fetching(self):
        
        raw_today_datetime = str(datetime.now())
        truncated_datetime = raw_today_datetime[:-7]
        today_datetime = truncated_datetime
        for rep in ('-', ':', ' '):
            today_datetime = today_datetime.replace(rep, '_')
            
        return today_datetime
      

# define model class
#==============================================================================
#==============================================================================
#==============================================================================
class PreProcessing:


    # Splits time series data into training and testing sets using TimeSeriesSplit
    #==========================================================================
    def roulette_colormapping(self, dataframe):
        
        '''
        '''
        color_map = {'black' : [15, 4, 2, 17, 6, 13, 11, 8, 10, 24, 33, 20, 31, 22, 29, 28, 35, 26],
                     'red' : [32, 19, 21, 25, 34, 27, 36, 30, 23, 5, 16, 1, 14, 9, 18, 7, 12, 3],
                     'green' : [0]}
        
        reverse_color_map = {v: k for k, values in color_map.items() for v in values}        
        dataframe['color encoding'] = dataframe['timeseries'].map(reverse_color_map)

        return dataframe

    
    # Splits time series data into training and testing sets using TimeSeriesSplit
    #==========================================================================
    def split_timeseries(self, dataframe, test_size, inverted=False):
        
        """
        timeseries_split(dataframe, test_size)
        
        Splits the input dataframe into training and testing sets based on the test size.
    
        Keyword arguments:  
        
        dataframe (pd.dataframe): the dataframe to be split
        test_size (float):        the proportion of data to be used as the test set
    
        Returns:
            
        df_train (pd.dataframe): the training set
        df_test (pd.dataframe):  the testing set
        
        """
        train_size = int(len(dataframe) * (1 - test_size))
        test_size = len(dataframe) - train_size 
        if inverted == True:
            df_train = dataframe.iloc[:test_size]
            df_test = dataframe.iloc[test_size:]
        else:
            df_train = dataframe.iloc[:train_size]
            df_test = dataframe.iloc[train_size:]

        return df_train, df_test 
    
    
    
    # generate n real samples with class labels; We randomly select n samples 
    # from the real data array
    #========================================================================== 
    def timeseries_labeling(self, df, window_size, output_size):
        
        """
        timeseries_labeling(dataframe, window_size)
    
        Labels time series data by splitting into input and output sequences using sliding window method.
    
        Keyword arguments:
            
        dataframe (pd.DataFrame): the time series data to be labeled
        window_size (int):        the number of time steps to use as input sequence
    
        Returns:
            
        X_array (np.ndarray):     the input sequence data
        Y_array (np.ndarray):     the output sequence data
        
        """        
        label = np.array(df)               
        X = [label[i : i + window_size] for i in range(len(label) - window_size - output_size + 1)]
        Y = [label[i + window_size : i + window_size + output_size] for i in range(len(label) - window_size - output_size + 1)]
        
        return np.array(X), np.array(Y)
        
    #==========================================================================
    def model_savefolder(self, path, model_name):

        '''
        Creates a folder with the current date and time to save the model.
    
        Keyword arguments:
            path (str):       A string containing the path where the folder will be created.
            model_name (str): A string containing the name of the model.
    
        Returns:
            str: A string containing the path of the folder where the model will be saved.
        
        '''        
        raw_today_datetime = str(datetime.now())
        truncated_datetime = raw_today_datetime[:-10]
        today_datetime = truncated_datetime.replace(':', '').replace('-', '').replace(' ', 'H') 
        model_name = f'{model_name}_{today_datetime}'
        model_savepath = os.path.join(path, model_name)
        if not os.path.exists(model_savepath):
            os.mkdir(model_savepath)               
            
        return model_savepath
    
    
     
    
    
   
     
