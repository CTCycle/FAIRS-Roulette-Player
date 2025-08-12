import os
import json

from FAIRS.app.constants import CONFIG_PATH


###############################################################################
class Configuration:
    
    def __init__(self):
        self.configuration = { 
            # Dataset
            'seed': 42,
            'sample_size': 1.0,
            'validation_size': 0.2,
            'shuffle_dataset': True,
            'shuffle_size': 256,
            'use_data_generator': False,
            # Model 
            'QNet_neurons': 64,
            'embedding_dimensions' : 200,
            'perceptive_field_size': 64,
            'jit_compile': False,
            'jit_backend': 'inductor',
            'exploration_rate' : 0.75,
            'exploration_rate_decay' : 0.995,
            'discount_rate' : 0.5,
            'model_update_frequency': 10,
             # Device
            'use_device_GPU': False,
            'device_id': 0,
            'use_mixed_precision': False,
            'num_workers': 0,

            # Training            
            'split_seed': 76,
            'train_seed': 42, 
            'train_sample_size': 1.0,
            'episodes': 100,
            'max_steps_episode': 2000,
            'additional_episodes': 10,
            'batch_size': 32,
            'learning_rate': 0.0001,
            'max_memory_size': 10000,
            'replay_buffer_size': 1000,
            'use_tensorboard': False,
            'plot_training_metrics' : True,
            'save_checkpoints': False,
            'checkpoints_frequency': 1,
            # environment
            'initial_capital': 1000,
            'bet_amount': 10,
            'render_environment': False,
            # inference
                  
            # Validation
            'val_batch_size': 20,
            'num_evaluation_images': 6            
        }

    #--------------------------------------------------------------------------  
    def get_configuration(self):
        return self.configuration
    
    #--------------------------------------------------------------------------
    def update_value(self, key: str, value: bool):       
        self.configuration[key] = value

    #--------------------------------------------------------------------------
    def save_configuration_to_json(self, name : str):  
        full_path = os.path.join(CONFIG_PATH, f'{name}.json')      
        with open(full_path, 'w') as f:
            json.dump(self.configuration, f, indent=4)

    #--------------------------------------------------------------------------
    def load_configuration_from_json(self, name : str):      
        full_path = os.path.join(CONFIG_PATH, name)
        with open(full_path, 'r') as f:
            self.configuration = json.load(f)