import os
import pickle
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder
from keras.utils.vis_utils import plot_model

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.commons.utils.preprocessing import PreProcessing
from FAIRS.commons.utils.models import ColorCodeModel, ModelTraining, model_savefolder
from FAIRS.commons.utils.callbacks import RealTimeHistory
from FAIRS.commons.pathfinder import DATA_PATH, CHECKPOINT_PATH
import FAIRS.commons.configurations as cnf


# [RUN MAIN]
if __name__ == '__main__':

    # 1. [LOAD DATA]
    #--------------------------------------------------------------------------     
    # Load extraction history data from the .csv datasets in the dataset folder    
    filepath = os.path.join(DATA_PATH, 'FAIRS_dataset.csv')                
    df_FAIRS = pd.read_csv(filepath, sep= ';', encoding='utf-8')

    # Sample a subset from the main dataset    
    num_samples = int(df_FAIRS.shape[0] * cnf.DATA_SIZE)
    df_FAIRS = df_FAIRS[(df_FAIRS.shape[0] - num_samples):]

    # 2. [PREPROCESS DATA]
    #--------------------------------------------------------------------------       
    # add number positions, map numbers to roulette color and reshape dataset    
    print(f'\nPreprocess data for FAIRS training')
    categories = [['green', 'black', 'red']]
    preprocessor = PreProcessing()
    categorical_encoder = OrdinalEncoder(categories=categories, 
                                         handle_unknown='use_encoded_value', 
                                         unknown_value=-1)
    df_FAIRS = preprocessor.roulette_colormapping(df_FAIRS, no_mapping=False)
    timeseries = categorical_encoder.fit_transform(df_FAIRS['encoding'].values.reshape(-1, 1))
    timeseries = pd.DataFrame(timeseries, columns=['encoding'])

    # split dataset into train and test and generate window-dataset    
    train_data, test_data = preprocessor.split_timeseries(timeseries, cnf.TEST_SIZE, inverted=cnf.INVERT_TEST) 
    X_train, Y_train = preprocessor.timeseries_labeling(train_data, cnf.WINDOW_SIZE) 
    X_test, Y_test = preprocessor.timeseries_labeling(test_data, cnf.WINDOW_SIZE)   
    train_samples, test_samples = train_data.shape[0], test_data.shape[0]

    # one hot encode the output for softmax training shape = (timesteps, features)    
    print('\nOne-Hot encode timeseries labels (Y data)')
    OH_encoder = OneHotEncoder(sparse=False)
    Y_train_OHE = OH_encoder.fit_transform(Y_train.reshape(Y_train.shape[0], -1))
    Y_test_OHE = OH_encoder.transform(Y_test.reshape(Y_test.shape[0], -1))

    # 2. [SAVE FILES]
    #--------------------------------------------------------------------------       
    # create model folder    
    model_folder_path, model_folder_name = model_savefolder(CHECKPOINT_PATH, 'FAIRSCCM')
    pp_path = os.path.join(model_folder_path, 'preprocessing')
    os.mkdir(pp_path) if not os.path.exists(pp_path) else None

    # save encoder    
    encoder_path = os.path.join(pp_path, 'categorical_encoder.pkl')
    with open(encoder_path, 'wb') as file:
        pickle.dump(categorical_encoder, file)

    # save npy files    
    print('\nSave preprocessed data on local hard drive')
    np.save(os.path.join(pp_path, 'train_data.npy'), X_train)
    np.save(os.path.join(pp_path, 'train_labels.npy'), Y_train_OHE)
    np.save(os.path.join(pp_path, 'test_data.npy'), X_test)
    np.save(os.path.join(pp_path, 'test_labels.npy'), Y_test_OHE)

    # 4. [DEFINE AND BUILD MODEL]    
    print('\nBuild the model and start training\n')
    trainer = ModelTraining(seed=cnf.SEED)
    trainer.set_device(device=cnf.ML_DEVICE, use_mixed_precision=cnf.MIXED_PRECISION)
    

    # initialize model class and build model    
    modelframe = ColorCodeModel(cnf.LEARNING_RATE, cnf.WINDOW_SIZE, cnf.EMBEDDING_SIZE, 
                                cnf.NUM_BLOCKS, cnf.NUM_HEADS, cnf.KERNEL_SIZE, 
                                seed=cnf.SEED, XLA_state=cnf.XLA_ACCELERATION)
    model = modelframe.get_model(summary=True)

    # plot model graph    
    if cnf.SAVE_MODEL_PLOT:
        plot_path = os.path.join(model_folder_path, 'FAIRSCCM_model.png')       
        plot_model(model, to_file = plot_path, show_shapes = True, 
                    show_layer_names = True, show_layer_activations = True, 
                    expand_nested = True, rankdir = 'TB', dpi = 400)

    # 4. [TRAINING MODEL]
    #--------------------------------------------------------------------------    
    # Setting callbacks and training routine for the features extraction model. 
    # use command prompt on the model folder and (upon activating environment), 
    # use the bash command: python -m tensorboard.main --logdir = tensorboard/

    most_freq_train = int(train_data.value_counts().idxmax()[0])
    most_freq_test = int(test_data.value_counts().idxmax()[0])

    print('TRAINING INFO\n')
    print(f'Number of timepoints in train dataset: {train_samples}')
    print(f'Number of timepoints in test dataset:  {test_samples}')    
    print(f'Number of epochs: {cnf.EPOCHS}')
    print(f'Window size:      {cnf.WINDOW_SIZE}')
    print(f'Batch size:       {cnf.BATCH_SIZE}')
    print(f'Learning rate:    {cnf.LEARNING_RATE}') 

    # initialize real time plot callback    
    RTH_callback = RealTimeHistory(model_folder_path)

    # setting for validation data    
    validation_data = (X_test, Y_test_OHE)   

    # initialize tensorboard    
    if cnf.USE_TENSORBOARD:
        log_path = os.path.join(model_folder_path, 'tensorboard')
        tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_path, histogram_freq=1)
        callbacks = [RTH_callback, tensorboard_callback]    
    else:    
        callbacks = [RTH_callback]

    # training loop    
    multiprocessing = cnf.NUM_PROCESSORS > 1
    training = model.fit(x=X_train, y=Y_train_OHE, batch_size=cnf.BATCH_SIZE, 
                        validation_data=validation_data, epochs=cnf.EPOCHS, 
                        callbacks=callbacks, workers=cnf.NUM_PROCESSORS, 
                        use_multiprocessing=multiprocessing)   
    
    # save model as savedmodel format
    model_file_path = os.path.join(model_folder_path, 'model')
    model.save(model_file_path)
    print(f'\nTraining session is over. Model has been saved in folder {model_folder_name}')

    # save model data and model parameters in txt files    
    parameters = {'model_name' : 'CCM',
                  'inverted_test' : cnf.INVERT_TEST,
                  'train_samples' : train_samples,
                  'test_samples' : test_samples,             
                  'window_size' : cnf.WINDOW_SIZE,              
                  'embedding_dimensions' : cnf.EMBEDDING_SIZE,
                  'num_blocks' : cnf.NUM_BLOCKS,
                  'num_heads' : cnf.NUM_HEADS,             
                  'batch_size' : cnf.BATCH_SIZE,
                  'learning_rate' : cnf.LEARNING_RATE,
                  'epochs' : cnf.EPOCHS}

    trainer.model_parameters(parameters, model_folder_path)





