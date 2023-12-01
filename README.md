# FAIRS-forecasting

## Project description
This script has been developed to allow roulette timeseries forecasting using a series of custom Recurrent Neural Network (RNN) models. Different approaches have been envisaged to accurately predict the probability of a number being the next extraction, by relying on both single number or categorical classification (black, red and green). THe rationale behind the different models is to use Long Short-Term Memory (LSTM) together with Embedding functionality for processing sequential data, having as output the probability distribution over possible next numbers. The input sequence is transformed into a dense vectors of fixed size, before being processed recursively by a series of LSTM layers with increasing neurons number. Once the temporal dependencies from the input sequence are learned by the model, a series of Dense layers map the extracted features to the output space. The final Dense layer is provided with softmax activation in order to output a probability distribution over possible next numbers. Overfitting is largely prevented by using Dropout layers in between.

## FAIRS Deep Learning models
FAIRS is based on two different deep learning (DL) forecasting models. Both models are structured as recurrent neural networks that use sequences of previous observations as inputs, and the next expected observation (or many of these) as output. 
...

### ColorCode Model (CCM)
...

### NumberMatrix Model (NMM)
...

## How to use
Run the FAIRS.py file to launch the script and use the main menu to navigate the different options. The main menu allows selecting one of the following options:

**1) FAIRS timeseries analysis:** Perform timeseries analysis to visualize distribution and main statistical parameters (work in progress).  

**2) FAIRS training: ColorCode Model (CCM)** Perform pretraining using the ColorCode model, which is focused on predicting the next color (green, black or red) to be extracted.

**3) FAIRS training: PositionMatrix Model (PMM)** Perform pretraining using the NumberMatrix model, which is focused on predicting raw numbers based on both previous extractions and the actual number position (following European Roulette encoding) 

**4) Predict next extraction:** Predict the next coming extraction using a pretrained model. Automatically infers which model has been loaded and forecast extractions accordingly.

**5) Exit and close**

### Configurations
The configurations.py file allows to change the script configuration. The following parameters are available:

- `generate_model_graph:` generate and save 2D model graph (as .png file)
- `use_mixed_precision:` whether or not to use mixed precision for faster training (mix float16/float32)
- `use_tensorboard:` activate or deactivate tensorboard logging
- `XLA_acceleration:` use of linear algebra acceleration for faster training 
- `training_device:` select the training device (CPU or GPU) 
- `neuron_baseline:` lowest number of neurons as reference 
- `epochs:` number of training iterations
- `learning_rate:` learning rate of the model during training
- `batch_size:` size of batches to be fed to the model during training
- `embedding_size:` embedding dimensions (valid for both models)
- `use_test_data:` whether or not to use test data
- `invert_test:` test data placement (True to set last points as test data)
- `data_size:` fraction of total available data to use
- `test_size:` fraction of data to leave as test data
- `window_size:` length of the input timeseries window
- `output_size:` number of next points to predict (output sequence)

### Requirements
This application has been developed and tested using the following dependencies (Python 3.10.12):

- `keras==2.10.0`
- `matplotlib==3.7.2`
- `numpy==1.25.2`
- `pandas==2.0.3`
- `scikit-learn==1.3.0`
- `seaborn==0.12.2`
- `tensorflow==2.10.0`
- `xlrd==2.0.1`
- `XlsxWriter==3.1.3`
- `pydot==1.4.2`
- `graphviz==0.20.1`

These dependencies are specified in the provided `requirements.txt` file to ensure full compatibility with the application. 
