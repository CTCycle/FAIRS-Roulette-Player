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
                   '2' : 'FAIRS training: ColorCode Model (CCM)',
                   '3' : 'FAIRS training: NumberMatrix Model (NMM)',
                   '4' : 'Predict next extraction',                                                 
                   '5' : 'Exit and close'}
model_menu = {'1' : 'Standard training',
              '2' : 'K-fold training',                                                          
              '3' : 'Exit and close'}


while True:
    print('------------------------------------------------------------------------')    
    op_sel = user_operations.menu_selection(operations_menu)
    print()     
    if op_sel == 1:
        import modules.timeseries_analysis
        del sys.modules['modules.timeseries_analysis'] 
    elif op_sel == 2:
        while True:    
            mod_sel = user_operations.menu_selection(model_menu)
            print()
            if mod_sel == 1:
                import modules.CCM_training
                del sys.modules['modules.CCM_training']
            elif mod_sel == 2: 
                import modules.CCM_kfold_training
                del sys.modules['modules.CCM_kfold_training']
            elif mod_sel == 3: 
                break
    elif op_sel == 3:
        while True:    
            mod_sel = user_operations.menu_selection(model_menu)
            print()
            if mod_sel == 1:
                import modules.NMM_training
                del sys.modules['modules.NMM_training']
            elif mod_sel == 2: 
                import modules.NMM_kfold_training
                del sys.modules['modules.NMM_kfold_training']
            elif mod_sel == 3: 
                break           
    elif op_sel == 4:
        import modules.FAIRS_forecast
        del sys.modules['modules.FAIRS_forecast']
    elif op_sel == 5:
        break
    
   






