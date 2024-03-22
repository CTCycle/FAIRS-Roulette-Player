# FAIRS: Fabulous Automated Intelligent Roulette Series

## 1. Project Overview
FAIRS is a project revolving around the forecasting of online roulette extractions, based on two different Neural Network (NN) models. Different approaches have been envisaged to accurately predict the probability of a number being extracted next, by relying on either the specific number or the categorical classification (black, red and green).  

## 2. FAIRS Deep Learning models
FAIRS relies on two different Deep Learning (DL) models with transformer encoder architecture for timeseries forecasting. The rationale behind the different models is to use the transformer encoder coupled with a feed forward convolutional network, to learn both long-term past dependencies and local patters in the extractionm sequence. Positional embedding is used to provide information about each extraction position in the timeseries, as due to the lack of recurrent architecture the model needs to know in advance the position of each timestep in the input sequences. The model output is the probability distribution of the next element, which is calculated using softmax activation. The two models are referred to as ColorCode Model (CCM) and NumberMatrix Model (NMM). 

### 2.1 ColorCode Model (CCM)
This model is built to predict the future color extractions based on previous observations, with the observed classes are encoded from raw numbers using the following mapping logic: 0 (green), 1 (black) and 2 (red). The input layer accepts sequences of a fixed window size, which is then encoded using positional embedding to convert the integer vectors into dense vectors of fixed size. This deep learning model uses a combination of transformer encoders and stacks of monodimensional convolutional layers, where multihead attention is used to apply self attention on the input sequences. Therefor, the network does not rely on recurrent architecture (e.g. Long Short-Term Memory (LSTM) networks), allowing to learn temporal sequence data by using the attention mechanisms on the sequences of previous observations. 

### 2.2 NumberMatrix Model (NMM)
This model is built to predict the next number extraction based on previous observations (for a totla of 37 different classes). Similarly to the ColorCode Model (CCM), this deep learning netwokr is based on transformer encoders followed by stacks of convolutional layers, where multihead attention is used to apply self attention on the input sequences. Again, this model does not rely on recurrent architecture as the temporal sequence logic is learned by using the attention mechanisms on previous observations, given the positional encoding of each extraction. Moreover, this model integrates in its input the roulette position for each number, in the attempt to provide information on the real-life arrangements of number on the roulette wheel. 

## 3. Installation 
First, ensure that you have Python 3.10.12 installed on your system. Then, you can easily install the required Python packages using the provided requirements.txt file:

`pip install -r requirements.txt` 

In addition to the Python packages, certain extra dependencies may be required for specific functionalities. These dependencies can be installed using conda or other external installation methods, depending on your operating system. Specifically, you will need to install graphviz and pydot to enable the visualization of the 2D model architecture:
- graphviz version 2.38.0
- pydot version 1.4.2

You can install these dependencies using the appropriate package manager for your system. For instance, you might use conda or an external installation method based on your operating system's requirements.

## 3.1 CUDA GPU Support (Optional, for GPU Acceleration)
If you have an NVIDIA GPU and want to harness the power of GPU acceleration using CUDA, please follow these additional steps. The application is built using TensorFlow 2.10.0 to ensure native Windows GPU support, so remember to install the appropriate versions:

### 3.1.1 Install NVIDIA CUDA Toolkit (Version 11.2)
To enable GPU acceleration, you'll need to install the NVIDIA CUDA Toolkit. Visit the [NVIDIA CUDA Toolkit download page](https://developer.nvidia.com/cuda-downloads) and select the version that matches your GPU and operating system. Follow the installation instructions provided. Alternatively, you can install `cuda-toolkit` as a package within your environment.

### 3.1.2 Install cuDNN (NVIDIA Deep Neural Network Library, Version 8.1.0.77)
Next, you'll need to install cuDNN, which is the NVIDIA Deep Neural Network Library. Visit the [cuDNN download page](https://developer.nvidia.com/cudnn) and download the cuDNN library version that corresponds to your CUDA version (in this case, version 8.1.0.77). Follow the installation instructions provided.

### 3.2 Additional Package (If CUDA Toolkit Is Installed)
If you've installed the NVIDIA CUDA Toolkit within your environment, you may also need to install an additional package called `cuda-nvcc` (Version 12.3.107). This package provides the CUDA compiler and tools necessary for building CUDA-enabled applications.

By following these steps, you can ensure that your environment is configured to take full advantage of GPU acceleration for enhanced performance.  

## 4. How to use
The project is organized into subfolders, each dedicated to specific tasks. The `utils/` folder houses crucial components utilized by various scripts. It's critical to avoid modifying these files, as doing so could compromise the overall integrity and functionality of the program.

**Data:** the roulette extraction timeseries file `FAIRS_dataset.csv` is contained in this folder. Run `data_validation.ipynb` to start a jupyter notebook for explorative data analysis (EDA) of the timeseries. 

**Model:** the necessary files for conducting model training and evaluation are located in this folder. `training/checkpoints` acts as the default repository where checkpoints of pre-trained models are stored. Run `model_training.py` to initiate the training process for deep learning models, or launch `model_evaluation.py` to evaluate the performance of pre-trained models.

**Inference:** use `roulette_forecasting.py` from this directory to predict the future roulette extractions based on the historical timeseries of previous extracted values. Depending on the selected model, the predicted values will be saved in `inference/predictions` folder with a different filename.

### 4.1 Configurations
The configurations.py file allows to change the script configuration. 

| Category                  | Setting                | Description                                                        |
|---------------------------|------------------------|--------------------------------------------------------------------|
| **Advanced settings**     | use_mixed_precision    | use mixed precision for faster training (float16/32)               |
|                           | use_tensorboard        | Activate/deactivate tensorboard logging                            |
|                           | XLA_acceleration       | Use linear algebra acceleration for faster training                |
|                           | training_device        | Select the training device (CPU or GPU)                            |
|                           | num_processors         | Number of processors (cores) to use; 1 disables multiprocessing    |
| **Training settings**      | epochs                 | Number of training iterations                                      |
|                           | learning_rate          | Learning rate of the model                                         |
|                           | batch_size             | Size of batches to be fed to the model during training             |
| **Model settings**        | embedding_size         | Embedding dimensions (valid for both models)                       |
|                           | num_blocks             | How many encoder layers to stack                                   |
|                           | num_heads              | Number of heads for multi-head attention mechanism                 |
|                           | generate_model_graph   | Generate and save 2D model graph (as .png file)                    |
| **Data settings**         | invert_test            | Where to place the test set (True to set last points as test data) |
|                           | data_size              | Fraction of total data to consider for training                    |
|                           | test_size              | Fraction of selected data to consider for test                     |
|                           | window_size            | Size of the timepoints window                                      |
| **General Settings**      | seed                   | Global random seed                                                 |
|                           | predictions_size       | Points to take from the original timeseries as prediction set      |

## License
This project is licensed under the terms of the MIT license. See the LICENSE file for details.

## Disclaimer
This project is for educational purposes only. It should not be used as a way to make easy money, since the model won't be able to accurately forecast numbers merely based on previous observations!