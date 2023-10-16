import os
import sys
import warnings
warnings.simplefilter(action='ignore', category = Warning)

# [IMPORT MODULES AND CLASSES]
#==============================================================================
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from modules.components.data_classes import UserOperations

# [MAIN MENU]
#==============================================================================
# module for the selection of different operations
#==============================================================================
user_operations = UserOperations()
operations_menu = {'1' : 'FAIRS timeseries analysis',
                   '2' : 'FAIRS training: Grouped Classes Method (GCM)',
                   '3' : 'FAIRS training: Full Encoding Method (FEM)',                                
                   '4' : 'Exit and close'}

GCM_menu = {'1' : 'Pretrain GCM model',
            '2' : 'Evaluate GCM model',
            '3' : 'Predict next extraction',
            '4' : 'Go back to main menu'}

FEM_menu = {'1' : 'Pretrain FEM model',
            '2' : 'Evaluate FEM model',
            '3' : 'Predict next extraction',
            '4' : 'Go back to main menu'}

while True:
    print('------------------------------------------------------------------------')
    print('FAIRS Project')
    print('------------------------------------------------------------------------')
    print()
    op_sel = user_operations.menu_selection(operations_menu)
    print() 
    
    if op_sel == 1:
        import modules.timeseries_analysis
        del sys.modules['modules.dataset_composer']

    elif op_sel == 2:        
        while True:
            sec_sel = user_operations.menu_selection(GCM_menu)
            print()
            if sec_sel == 1:
                import modules.GCM_training
                del sys.modules['modules.GCM_training']
            elif sec_sel == 2:
                pass
            elif sec_sel == 3:
                import modules.GCM_predictions
                del sys.modules['modules.GCM_predictions']
            elif sec_sel == 4:
                break

    elif op_sel == 3:        
        while True:
            sec_sel = user_operations.menu_selection(FEM_menu)
            print()
            if sec_sel == 1:
                pass
                # import modules.FEM_training
                # del sys.modules['modules.FEM_training']
            elif sec_sel == 2:
                pass
            elif sec_sel == 3:
                # import modules.FEM_predictions
                # del sys.modules['modules.FEM_predictions']
                pass
            elif sec_sel == 4:
                break
        
    elif op_sel == 4:
        break
    
   






