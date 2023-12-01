import os
import sys
import art
import warnings
warnings.simplefilter(action='ignore', category = Warning)

# import modules and classes
#------------------------------------------------------------------------------
from modules.components.data_classes import UserOperations

# welcome message
#------------------------------------------------------------------------------
ascii_art = art.text2art('FAIRS')
print(ascii_art)

# [MAIN MENU]
#==============================================================================
# module for the selection of different operations
#==============================================================================
user_operations = UserOperations()
operations_menu = {'1' : 'Data analysis',
                   '2' : 'FAIRS training: CombinedCode Model (CCM)',
                   '3' : 'FAIRS training: PositionMatrix Model (PMM)',
                   '4' : 'Predict next extraction',                                                 
                   '5' : 'Exit and close'}

while True:
    print('------------------------------------------------------------------------')    
    op_sel = user_operations.menu_selection(operations_menu)
    print()     
    if op_sel == 1:
        import modules.timeseries_analysis
        del sys.modules['modules.CCM_training'] 
    elif op_sel == 2:
        import modules.CCM_training
        del sys.modules['modules.CCM_training']
    elif op_sel == 2:
        import modules.PMM_training
        del sys.modules['modules.PMM_training']           
    elif op_sel == 3:
        import modules.timeseries_predictions
        del sys.modules['modules.timeseries_predictions']
    elif op_sel == 4:
        break
    
   






