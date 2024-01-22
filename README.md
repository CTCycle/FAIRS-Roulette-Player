# FAIRS-forecasting

## Project description
This script has been developed to allow roulette timeseries forecasting using a series of custom Neural Network (NN) models. Different approaches have been envisaged to accurately predict the probability of a number being extracted next, by relying on either the specific number or the categorical classification (black, red and green).  

## FAIRS Deep Learning models
FAIRS relies on two different Deep Learning (DL) models with transformer encoder architecture for timeseries forecasting. The rationale behind the different models is to use the transformer encoder coupled with a feed forward convolutional network, to learn both long-term past dependencies and local patters in the extractionm sequence. Positional embedding is used to provide information about each extraction position in the timeseries, as due to the lack of recurrent architecture the model needs to know in advance the position of each timestep in the input sequences.  The model output is the probability distribution of the next element, which is calculated using softmax activation. The two models are referred to as ColorCode Model (CCM) and NumberMatrix Model (NMM). 

### ColorCode Model (CCM)
This model is built to predict the future color extractions based on previous observations, with the observed classes are encoded from raw numbers using the following mapping logic: 0 (green), 1 (black) and 2 (red). The input layer accepts sequences of a fixed window size, which is then encoded using positional embedding to convert the integer vectors into dense vectors of fixed size. This deep learning model uses a combination of transformer encoders and stacks of convolutional layers (feed forward module), where multihead attention is used to apply self attention on the input sequences. As such, the network does not rely on recurrent architecture (e.g. Long Short-Term Memory (LSTM) networks), allowing to learn temporal sequence data by using the attention mechanisms on previous observations. 

### NumberMatrix Model (NMM)
This model is built to predict the next number extraction based on previous observations (for a totla of 37 different classes). Similarly to the ColorCode Model (CCM), this deep learning netwokr is based on transformer encoders followed by  stacks of convolutional layers (feed forward module), where multihead attention is used to apply self attention on the input sequences. Again, this model does not rely on recurrent architecture as the temporal sequence logic is learned by using the attention mechanisms on previous observations, given the positional encoding of each extraction. Moreover, this model intergates in its input the roulette position for each number, in the attempt to provide information on the real-life arrangements of number on the roulette wheel. 

## How to use
Run the FAIRS.py file to launch the script and use the main menu to navigate the different options. The main menu allows selecting one of the following options (when selecting a pretraining method, another menu will be presented to allow the user chosing between the ColorCode and the NumberMatrix models):

**1) Timeseries analysis:** Perform timeseries analysis to visualize distribution and main statistical parameters (work in progress).  

**2) Standard model pretraining** Allows training the DL models throughout multiple epochs, using the entire dataset (or a part of it) as the training set.

**3) Predict next extraction:** Predict the next coming extraction using a pretrained model. Automatically infers which model has been loaded and forecast extractions accordingly.

**4) Exit and close**

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
- `num_blocks:` how many encoder layers to stack
- `num_heads:` number of heads for multi-head attention mechanism

**Settings for data preprocessing and predictions:**
- `use_test_data:` whether or not to use test data
- `invert_test:` test data placement (True to set last points as test data)
- `data_size:` fraction of total available data to use
- `test_size:` fraction of data to leave as test data
- `window_size:` length of the input timeseries window
- `output_size:` number of next points to predict (output sequence)
- `predictions_size:` number of timeseries points to take for the predictions inputs

## Installation 
First, ensure that you have Python 3.10.12 installed on your system. Then, you can easily install the required Python packages using the provided requirements.txt file:

`pip install -r requirements.txt` 

In addition to the Python packages, certain extra dependencies may be required for specific functionalities. These dependencies can be installed using conda or other external installation methods, depending on your operating system. Specifically, you will need to install graphviz and pydot to enable the visualization of the 2D model architecture:
- graphviz version 2.38.0
- pydot version 1.4.2

You can install these dependencies using the appropriate package manager for your system. For instance, you might use conda or an external installation method based on your operating system's requirements.

## CUDA GPU Support (Optional, for GPU Acceleration)
If you have an NVIDIA GPU and want to harness the power of GPU acceleration using CUDA, please follow these additional steps. The application is built using TensorFlow 2.10.0 to ensure native Windows GPU support, so remember to install the appropriate versions:

### 1. Install NVIDIA CUDA Toolkit (Version 11.2)

To enable GPU acceleration, you'll need to install the NVIDIA CUDA Toolkit. Visit the [NVIDIA CUDA Toolkit download page](https://developer.nvidia.com/cuda-downloads) and select the version that matches your GPU and operating system. Follow the installation instructions provided. Alternatively, you can install `cuda-toolkit` as a package within your environment.

### 2. Install cuDNN (NVIDIA Deep Neural Network Library, Version 8.1.0.77)

Next, you'll need to install cuDNN, which is the NVIDIA Deep Neural Network Library. Visit the [cuDNN download page](https://developer.nvidia.com/cudnn) and download the cuDNN library version that corresponds to your CUDA version (in this case, version 8.1.0.77). Follow the installation instructions provided.

### 3. Additional Package (If CUDA Toolkit Is Installed)

If you've installed the NVIDIA CUDA Toolkit within your environment, you may also need to install an additional package called `cuda-nvcc` (Version 12.3.107). This package provides the CUDA compiler and tools necessary for building CUDA-enabled applications.

By following these steps, you can ensure that your environment is configured to take full advantage of GPU acceleration for enhanced performance.                 

## License
This project is licensed under the terms of the MIT license. See the LICENSE file for details.

## Disclaimer
This project is for educational purposes only. It should not be used as a way to make easy money, since the model won't be able to accurately forecast numbers merely based on previous observations!