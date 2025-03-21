# FAIRS: Fabulous Automated Intelligent Roulette System

## 1. Project Overview
FAIRS is a research project dedicated to predicting upcoming outcomes in online roulette through a Deep Q-Network (DQN) agent. Instead of relying solely on immediate, isolated results, FAIRS utilizes sequences of past roulette spins, incorporating a perceptive field of historical outcomes as input. This approach allows the model to detect temporal patterns that might influence future events. Additionally, random number generation can be used to simulate a genuinely unpredictable game environment, mirroring the behavior of a real roulette wheel.

During training, the DQN agent learns to identify patterns within these sequences, and to select the actions associated with the highest Q-scores—signals of potentially more rewarding decisions. In doing so, FAIRS adapts sequence modeling techniques to the inherently random and structured nature of roulette outcomes, aiming to refine predictive accuracy in an environment defined by uncertainty.

## 2. FAIRSnet model
FAIRSnet is a custom neural network architecture tailored for time series forecasting in roulette prediction. It combines dense layers, frequency-based embeddings, and dual Q-Networks to capture sequential dependencies. The model takes a perceived field of historical outcomes as input, passing these sequences through a frequency-based embedding layer. While roulette outcomes are theoretically random, some online platforms may use algorithms that exhibit patterns or slight autoregressive tendencies. The architecture employs multiple dense layers with ReLU activation to learn relationships between past states and actions with the highest expected rewards. It is trained on a dataset built from past experiences, using reinforcement learning to optimize decision-making through DQN policy. The Q-Network head predicts Q-values that represents the confidence level for each possible outcome (suggested action). The model is trained using the Mean Squared Error (MSE) loss function, while tracking the Mean Absolute Percentage Error (MAPE) as a key metric. 

## 3. Installation
The installation process on Windows has been designed to be fully automated. To begin, simply run *start_on_windows.bat.* On its first execution, the installation procedure will execute with minimal user input required. The script will check if either Anaconda or Miniconda is installed and can be accessed from your system path. If neither is found, it will automatically download and install the latest Miniconda release from https://docs.anaconda.com/miniconda/. Following this step, the script will proceed with the installation of all necessary Python dependencies. 

This includes Keras 3 (with PyTorch support as the backend) and the required CUDA dependencies (CUDA 12.4) to enable GPU acceleration. Should you prefer to handle the installation process separately, you can run the standalone installer by running *setup/install_on_windows.bat*.

**Important:** After installation, if the project folder is moved or its path is changed, the application will no longer function correctly. To fix this, you can either:

- Open the main menu, select *Setup and maintentance* and choose *Install project in editable mode*
- Manually run the following commands in the terminal, ensuring the project folder is set as the current working directory (CWD):

    `conda activate FEXT`

    `pip install -e . --use-pep517` 

### 3.1 Just-In-Time (JIT) Compiler
This project leverages Just-In-Time model compilation through `torch.compile`, enhancing model performance by tracing the computation graph and applying advanced optimizations like kernel fusion and graph lowering. This approach significantly reduces computation time during both training and inference. The default backend, TorchInductor, is designed to maximize performance on both CPUs and GPUs. Additionally, the installation includes Triton, which generates highly optimized GPU kernels for even faster computation on NVIDIA hardware. For Windows users, a precompiled Triton wheel is bundled with the installation, ensuring seamless integration and performance improvements.

## 4. How to use
On Windows, run *start_on_windows.bat* to launch the main navigation menu and browse through the various options. Please note that some antivirus software, such as Avast, may flag or quarantine python.exe when called by the .bat file. If you encounter unusual behavior, consider adding an exception for your Anaconda or Miniconda environments in your antivirus settings.

### 4.1 Navigation menu

**1) Data analysis:** performs data validation using a series of metrics to analyze roulette extractions. 

**2) Model training and evaluation:** open the machine learning menu to explore various options for model training and validation. Once the menu is open, you will see different options:
- **train from scratch:** start training the FAIRS model using reinforcement learning in a roulette-based environment. This option starts a training from scratch using either true roulette extraction series or a random number generator. 
- **train from checkpoint:** start training a pretrained FAIRS checkpoint for an additional amount of episodes, using the pretrained model settings and data (CURRENTLY NOT IMPLEMENTED!) 
- **model evaluation:** evaluate the performance of pretrained model checkpoints using different metrics. 

**3) Predict roulette extractions:** predict the future roulette extractions based on the historical timeseries, and also start the real time playing mode.  

**4) Setup and Maintenance:** execute optional commands such as *Install project into environment* to reinstall the project within your environment, *update project* to pull the last updates from github, and *remove logs* to remove all logs saved in *resources/logs*.  

**5) Exit:** close the program immediately 

### 4.2 Resources
This folder organizes data and results across various stages of the project, such as data validation, model training, and evaluation. By default, all data is stored within an SQLite database; however, users have the option to export data into separate CSV files if desired. To visualize and interact with SQLite database files, we recommend downloading and installing the DB Browser for SQLite, available at: https://sqlitebrowser.org/dl/.

The directory structure includes the following folders:

- **checkpoints:**  pretrained model checkpoints are stored here, and can be used either for resuming training or performing inference with an already trained model.

- **database:** Processed data and validation results will be stored centrally within the main database *FEXT_database.db*. All associated metadata will be promptly stored in *database/metadata*. For image training data, ensure all image files are placed in *database/images*, adhering to specified formats (.jpeg or .png). Graphical validation outputs will be saved separately within *database/validation*. Stores roulette extraction series through the file *FAIRS_dataset.csv*.

- **inference:** this is where roulette predictions are stored in .csv format, and where the file holding past extraction to start predictions from is stored (*FAIRS_predictions.csv*).

- **logs:** log files are saved here

- **templates:** reference template files can be found here

## 5. Configurations
For customization, you can modify the main configuration parameters using *settings/configurations.json* 

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
| PERCEPTIVE_FIELD   | Size of past experiences window                          | 
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
| RENDERING          | Whether to render the roulette wheel progress            |

#### Agent Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| DISCOUNT RATE      | How important are future rewards over immediate ones     |
| EXPLORATION_RATE   | Tendency to explore (random actions)                     |
| ER_DECAY           | Decay factor for the exploration rate                    | 
| MINIMUM_ER         | Minimum allowed value of exploration rate                |
| REPLAY_BUFFER      | Size of the experience replay buffer                     |
| MEMORY             | Size of past experience memory                           |

#### Training Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| EPISODES           | Number of episodes (epochs) to train the model           |
| ADDITIONAL_EPISODES| Number of additional episodes to further train checkpoint|
| LEARNING_RATE      | Learning rate for the optimizer                          |
| BATCH_SIZE         | Number of samples per batch                              |
| UPDATE_FREQUENCY   | Number of timesteps to wait before updating model        |
| USE_TENSORBOARD    | Whether to use TensorBoard for logging                   |
| SAVE_CHECKPOINTS   | Save checkpoints during training (at each epoch)         |

#### Inference Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| DATA_FRACTION      | Fraction of past data to start the predictions from      | 
| ONLINE             | Toggle the real time playing mode on or off              |

#### Validation Configuration

| Parameter          | Description                                              |
|--------------------|----------------------------------------------------------|
| BATCH_SIZE         | Number of samples per batch                              |
| NUM_IMAGES         | Max number of images to compare during evaluation        |
| DPI                | Resolution of figures from validation                    |


**Environmental variables** are stored in *setup/variables/.env*. For security reasons, this file is typically not uploaded to GitHub. Instead, you must create this file manually by copying the template from *resources/templates/.env* and placing it in the *setup/variables* directory.

| Variable              | Description                                              |
|-----------------------|----------------------------------------------------------|
| KERAS_BACKEND         | Sets the backend for Keras, default is PyTorch           |
| TF_CPP_MIN_LOG_LEVEL  | TensorFlow logging verbosity                             |

## 6. License
This project is licensed under the terms of the MIT license. See the LICENSE file for details.

## Disclaimer
This project is for educational purposes only. It should not be used as a way to make easy money, since the model won't be able to accurately forecast numbers merely based on previous observations!