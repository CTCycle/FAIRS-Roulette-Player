# FAIRS: Fabulous Automated Intelligent Roulette System

## 1. Project Overview
FAIRS is a project aimed at predicting the next outcome in online roulette using a Deep Q-Network (DQN) agent. Unlike conventional approaches, FAIRS leverages sequences of actual roulette results, which can be stored in any .csv file, and uses a perceived field (a sliding window of historical outcomes) as input for its predictions. Alternatively, numbers can be generated randomly to simulate a truly random game, as a real roulette wheel should operate. The DQN agent is trained to identify patterns in these sequences and predict the highest Q-scores, which indicate the most rewarding actions. This approach adapts sequence modeling techniques to the unique structure and inherent randomness of roulette data.

## 2. FAIRSnet model
FAIRSnet is a custom neural network architecture tailored for time series forecasting in roulette prediction. It combines dense layers, frequency-based embeddings, and dual Q-Networks to capture sequential dependencies. The model takes a perceived field of historical outcomes as input, passing these sequences through a frequency-based embedding layer. While roulette outcomes are theoretically random, some online platforms may use algorithms that exhibit patterns or slight autoregressive tendencies.

The architecture employs multiple dense layers with ReLU activation to learn relationships between past states and actions with the highest expected rewards. It is trained on a dataset built from past experiences, using reinforcement learning to optimize decision-making. FAIRSnet features a Q-Network head that predicts Q-values, representing the confidence level for each possible outcome. These predictions are output as a probability distribution for the next best action in the game.

The model is trained using the Mean Squared Error (MSE) loss function, while tracking the Mean Absolute Percentage Error (MAPE) as a key metric. This structure enables FAIRSnet to effectively analyze roulette data, even in scenarios where outcomes may exhibit subtle, algorithmic patterns.

## 3. Installation
The installation process on Windows has been designed for simplicity and ease of use. To begin, simply run `FAIRS.bat`. On its first execution, the installation procedure will automatically start with minimal user input required. The script will check if either Anaconda or Miniconda is installed on your system. If neither is found, you will need to install it manually. You can download and install Miniconda by following the instructions here: https://docs.anaconda.com/miniconda/.

After setting up Anaconda/Miniconda, the installation script will install all the necessary Python dependencies. This includes Keras 3 (with PyTorch support as the backend) and the required CUDA dependencies (CUDA 12.1) to enable GPU acceleration. If you'd prefer to handle the installation process separately, you can run the standalone installer by executing `setup/FAIRS_installer.bat`. You can also use a custom python environment by modifying `settings/launcher_configurations.ini` and setting use_custom_environment as true, while specifying the name of your custom environment.

**Important:** After installation, if the project folder is moved or its path is changed, the application will no longer function correctly. To fix this, you can either:

- Open the main menu, select "FAIRS setup," and choose "Install project packages"
- Manually run the following commands in the terminal, ensuring the project folder is set as the current working directory (CWD):

    `conda activate FAIRS`

    `pip install -e . --use-pep517` 

### 3.1 Just-In-Time (JIT) Compiler
This project leverages Just-In-Time model compilation through `torch.compile`, enhancing model performance by tracing the computation graph and applying advanced optimizations like kernel fusion and graph lowering. This approach significantly reduces computation time during both training and inference. The default backend, TorchInductor, is designed to maximize performance on both CPUs and GPUs. Additionally, the installation includes Triton, which generates highly optimized GPU kernels for even faster computation on NVIDIA hardware. For Windows users, a precompiled Triton wheel is bundled with the installation, ensuring seamless integration and performance improvements.

## 4. How to use
On Windows, run `FAIRS.bat` to launch the main navigation menu and browse through the various options. Alternatively, you can run each file separately using `python path/filename.py` or `jupyter path/notebook.ipynb`. 

### 4.1 Navigation menu

**1) Data analysis:** run `validation/data_validation.ipynb` to perform data validation using a series of metrics to analyze roulette extractions. 

**2) Model training and evaluation:** open the machine learning menu to explore various options for model training and validation. Once the menu is open, you will see different options:
- **train from scratch:** runs `training/model_training.py` to start training the FAIRS model using reinforcement learning in a roulette-based environment. This option starts a training from scratch using either true roulette extraction series or a random number generator. 
- **train from checkpoint:** runs `training/train_from_checkpoint.py` to start training a pretrained FAIRS checkpoint for an additional amount of episodes, using the pretrained model settings and data.  
- **model evaluation:** run `validation/model_validation.ipynb` to evaluate the performance of pretrained model checkpoints using different metrics. 

**3) Predict roulette extractions:** runs `inference/roulette_forecasting.py` to predict the future roulette extractions based on the historical timeseries.  

**4) FAIRS setup:** allows running some options command such as **install project packages** to run the developer model project installation, and **remove logs** to remove all logs saved in `resources/logs`. 

**5) Exit and close** 

### 4.2 Resources

- **checkpoints:**  pretrained model checkpoints are stored here, and can be used either for resuming training or performing inference with an already trained model.

- **dataset:** contains the main rouklette extraction file `FAIRS_dataset.csv`.

- **predictions:** this is the place where roulette predictions are stored in csv format. 

- **logs:** the application logs are saved within this folder

- **validation:** Used to save the results of data validation processes. This helps in keeping track of validation metrics and logs.


## 5. Configurations
For customization, you can modify the main configuration parameters using `settings/app_configurations.json` 

#### Dataset Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| FROM_GENERATOR     | Whether to use a randon number generator                 |
| SAMPLE_SIZE        | Number of samples to use from the dataset                |
| VALIDATION_SIZE    | Proportion of the dataset to use for validation          |
| PERCEPTIVE_SIZE    | Size of the perceptive field of past extractions         |


#### Model Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| EMBEDDING_DIMS     | Embedding dimensions (valid for both models)             |  
| UNITS              | Number of neurons in the starting layer                  | 
| JIT_COMPILE        | Apply Just-In_time (JIT) compiler for model optimization |
| JIT_BACKEND        | Just-In_time (JIT) backend                               |

#### Device Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| DEVICE             | Device to use for training (e.g., GPU)                   |
| DEVICE ID          | ID of the device (only used if GPU is selected)          |
| MIXED_PRECISION    | Whether to use mixed precision training                  |
| NUM_PROCESSORS     | Number of processors to use for data loading             |

#### Environment Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| INITIAL_CAPITAL    | Total capital at the beginning of each episode           |
| BET_AMOUNT         | Amount to bet each time step                             |
| MAX_STEPS          | Maximum steps number per episode                         |
| RENDERING          | Whether to render the roulette wheel progress           |

#### Agent Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| EPOCHS             | Number of epochs to train the model                      |
| LEARNING_RATE      | Learning rate for the optimizer                          |
| BATCH_SIZE         | Number of samples per batch                              |
| MIXED_PRECISION    | Whether to use mixed precision training                  |
| USE_TENSORBOARD    | Whether to use TensorBoard for logging                   |
| XLA_STATE          | Whether to enable XLA (Accelerated Linear Algebra)       |
| ML_DEVICE          | Device to use for training (e.g., GPU)                   |
| NUM_PROCESSORS     | Number of processors to use for data loading             |     

#### Training Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| EPOCHS             | Number of epochs to train the model                      |
| LEARNING_RATE      | Learning rate for the optimizer                          |
| BATCH_SIZE         | Number of samples per batch                              |
| MIXED_PRECISION    | Whether to use mixed precision training                  |
| USE_TENSORBOARD    | Whether to use TensorBoard for logging                   |


#### Evaluation Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| BATCH_SIZE         | Number of samples per batch during evaluation            | 
| SAMPLE_SIZE        | Number of samples from the dataset (evaluation only)     |
| VALIDATION_SIZE    | Fraction of validation data (evaluation only)            |

## 6. License
This project is licensed under the terms of the MIT license. See the LICENSE file for details.

## Disclaimer
This project is for educational purposes only. It should not be used as a way to make easy money, since the model won't be able to accurately forecast numbers merely based on previous observations!