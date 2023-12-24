# FAIRS-forecasting

## Project description
This script has been developed to allow roulette timeseries forecasting using a series of custom Recurrent Neural Network (RNN) models. Different approaches have been envisaged to accurately predict the probability of a number being extracted next, by relying on both single number or categorical classification (black, red and green). THe rationale behind the different models is to use Long Short-Term Memory (LSTM) together with Embedding functionality for processing sequential data, having as output the probability distribution over possible next numbers. The input sequence is transformed into a dense vectors of fixed size, before being processed recursively by a series of LSTM layers with increasing neurons number. Once the temporal dependencies from the input sequence are learned by the model, a series of Dense layers map the extracted features to the output space. The final Dense layer is provided with softmax activation in order to output a probability distribution over possible next numbers. Overfitting is largely prevented by using Dropout layers in between.

## FAIRS Deep Learning models
FAIRS relies on two different Deep Learning (DL) models with recurrent network architecture (for timeseries forecasting). Both models are structured as a combination of convolutional and recurrent neural networks that use fixed-length sequences of past observations as inputs, while the next expected observation (or a fixed-length sequence of these) as output. The two models are referred to as ColorCode Model (CCM) and NumberMatrix Model (NMM). 

### ColorCode Model (CCM)
This model is built to predict the future color extractions based on previous observations. Colors are encoded with integers following the mapping logic: green is 0, red is 1 and black is 2. This deep learning model uses a combination of Convolutional Neural Networks (CNNs), Long Short-Term Memory (LSTM) networks, and Dense layers. The input layer accepts sequences of a fixed window size, which is then encoded using embedding to convert the integer vectors into dense vectors of fixed size. The embedded sequences are passed through three convolutional layers, each followed by a max-pooling layer, where the increasing number of filters allows for data thickening. The LSTM layers perform recurrent operations to keep memory of past observations within single batches of data (stateless mode), considering sufficiently long sequences as bearing important information. The output from the LSTM layers is repeated to match the desired output size using a repeated vector layer, and then a series of dense layers with bartch normalization and dropout are used to generate the future outputs with a softmax activation function.

### NumberMatrix Model (NMM)
...

## How to use
Run the FAIRS.py file to launch the script and use the main menu to navigate the different options. The main menu allows selecting one of the following options (when selecting a pretraining method, another menu will be presented to allow the user chosing between the ColorCode and the NumberMatrix models):

**1) Timeseries analysis:** Perform timeseries analysis to visualize distribution and main statistical parameters (work in progress).  

**2) Standard model pretraining** Allows training the DL models throughout multiple epochs, using the entire dataset (or a part of it) as the training set.

**3) K-fold model pretraining** Perform pretraining using the K-fold method for cross-validation, by splitting the entire datasets into subsets and training the model on each subset separately. 

**4) Predict next extraction:** Predict the next coming extraction using a pretrained model. Automatically infers which model has been loaded and forecast extractions accordingly.

**5) Exit and close**

### Configurations
The configurations.py file allows to change the script configuration. The following parameters are available:

**Settings for training performance and monitoring options:**
- `generate_model_graph:` generate and save 2D model graph (as .png file)
- `use_mixed_precision:` whether or not to use mixed precision for faster training (mix float16/float32)
- `use_tensorboard:` activate or deactivate tensorboard logging
- `XLA_acceleration:` use of linear algebra acceleration for faster training 

**Settings for pretraining parameters:**
- `training_device:` select the training device (CPU or GPU)
- `epochs:` number of training iterations
- `learning_rate:` learning rate of the model during training
- `batch_size:` size of batches to be fed to the model during training
- `embedding_size:` embedding dimensions (valid for both models)

**Settings for data preprocessing and predictions:**
- `use_test_data:` whether or not to use test data
- `invert_test:` test data placement (True to set last points as test data)
- `data_size:` fraction of total available data to use
- `test_size:` fraction of data to leave as test data
- `window_size:` length of the input timeseries window
- `output_size:` number of next points to predict (output sequence)
- `predictions_size:` number of timeseries points to take for the predictions inputs


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

## License
This project is licensed under the terms of the MIT license. See the LICENSE file for details.

## Disclaimer
This project is for educational purposes only. It should not be used as a way to make easy money, since the model won't be able to accurately forecast numbers merely based on previous observations!