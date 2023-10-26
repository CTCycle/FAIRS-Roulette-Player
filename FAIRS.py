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
operations_menu = {'1' : 'FAIRS timeseries analysis',
                   '2' : 'FAIRS training: Color Code Model (CCM)',                                                   
                   '3' : 'Exit and close'}

CCM_menu = {'1' : 'Pretrain ColorCode model',
            '2' : 'Evaluate ColorCode model',
            '3' : 'Predict next extraction',
            '4' : 'Go back to main menu'}

while True:
    print('------------------------------------------------------------------------')    
    op_sel = user_operations.menu_selection(operations_menu)
    print() 
    
    if op_sel == 1:
        import modules.timeseries_analysis
        del sys.modules['modules.dataset_composer']

    elif op_sel == 2:        
        while True:
            sec_sel = user_operations.menu_selection(CCM_menu)
            print()
            if sec_sel == 1:
                import modules.CCM_training
                del sys.modules['modules.CCM_training']
            elif sec_sel == 2:
                pass
            elif sec_sel == 3:
                import modules.CCM_predictions
                del sys.modules['modules.CCM_predictions']
            elif sec_sel == 4:
                break    
        
    elif op_sel == 4:
        break
    
   






