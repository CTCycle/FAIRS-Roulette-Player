# FAIRS: Fabulous Automated Intelligent Roulette System

## 1. Introduction
FAIRS is a research project dedicated to predicting upcoming outcomes in online roulette through a Deep Q-Network (DQN) agent. Instead of relying solely on immediate, isolated results, FAIRS utilizes sequences of past roulette spins, incorporating a perceptive field of historical outcomes as input. This approach allows the model to detect temporal patterns that might influence future events. Additionally, random number generation can be used to simulate a genuinely unpredictable game environment, mirroring the behavior of a real roulette wheel.

During training, the DQN agent learns to identify patterns within these sequences, and to select the actions associated with the highest Q-scores—signals of potentially more rewarding decisions. In doing so, FAIRS adapts sequence modeling techniques to the inherently random and structured nature of roulette outcomes, aiming to refine predictive accuracy in an environment defined by uncertainty.

## 2. FAIRSnet model
FAIRSnet is a specialized neural network designed for roulette prediction within reinforcement learning contexts. Its core objective is forecasting the action most likely to yield the highest reward by analyzing the current state of the game, represented by a predefined series of recent outcomes (the perceived field). The model learns through interactions with the roulette environment, exploring multiple strategic betting options, including:

- Betting on a specific number (0–36)
- Betting on color outcomes (red or black)
- Betting on numerical ranges (high or low)
- Betting on specific dozen ranges
- Choosing to abstain from betting and exit the game

 While roulette outcomes are theoretically random, some online platforms may use algorithms that exhibit patterns or slight autoregressive tendencies. The model is trained on a dataset built from past experiences, using reinforcement learning to optimize decision-making through DQN policy. The Q-Network head predicts Q-values that represents the confidence level for each possible outcome (suggested action). The model is trained using the Mean Squared Error (MSE) loss function, while tracking the Mean Absolute Percentage Error (MAPE) as a key metric. 

## 3. Installation
The installation process for Windows is fully automated. Simply run the script *start_on_windows.bat* to begin. During its initial execution, the script installs portable Python, necessary dependencies, minimizing user interaction and ensuring all components are ready for local use. 

### 3.1 Just-In-Time (JIT) Compiler
This project leverages Just-In-Time model compilation through `torch.compile`, enhancing model performance by tracing the computation graph and applying advanced optimizations like kernel fusion and graph lowering. This approach significantly reduces computation time during both training and inference. The default backend, TorchInductor, is designed to maximize performance on both CPUs and GPUs. Additionally, the installation includes Triton, which generates highly optimized GPU kernels for even faster computation on NVIDIA hardware. 

## 4. How to use
On Windows, run *start_on_windows.bat* to launch the application. Please note that some antivirus software, such as Avast, may flag or quarantine python.exe when called by the .bat file. If you encounter unusual behavior, consider adding an exception in your antivirus settings.

The main interface streamlines navigation across the application's core services, including dataset evaluation, model training and evaluation, and inference. Users can easily visualize generated plots and browse both training and inference images. Models training supports customizable configurations and also allows resuming previous sessions using pretrained models.

**Dataset validation and processing:** Load data into the database from the provided csv sources. The dataset can be analyzed and validated using different metrics. 

- **Calculation of roulette transitions**: visualize transitions between events from the roulette series

**Model:** this tab gives access to FAIRS model training from scratch or training resumption from previous checkpoints. Data processing is done in runtime prior to training, by encoding extraction based on color and position on the roulette wheel. Moreover, this section provides both model inference and evaluation features. Use the pretrained DQN agent to predict roulette extractions in real time using the dedicated console. Eventually, the DQN agent can be evaluated using different metrics, such as:

- **Average mean sparse categorical loss and accuracy** 
- **...** 

**Viewer:** real time data visualization, coming soon! 

## 4.1 Setup and Maintenance
You can run *setup_and_maintenance.bat* to start the external tools for maintenance with the following options:

- **Update project:** check for updates from Github
- **Remove logs:** remove all logs file from *resources/logs*

### 4.2 Resources
This folder organizes data and results across various stages of the project, such as data validation, model training, and evaluation. By default, all data is stored within an SQLite database; however, users have the option to export data into separate CSV files if desired. To visualize and interact with SQLite database files, we recommend downloading and installing the DB Browser for SQLite, available at: https://sqlitebrowser.org/dl/. The directory structure includes the following folders:

- **checkpoints:**  pretrained model checkpoints are stored here, and can be used either for resuming training or performing inference with an already trained model.

- **database:** collected adsorption data, processed data and validation results will be stored centrally within the main database *FAIRS_database.db*. Validation outputs will be saved separately within *database/validation*. Data used for inference with a pretrained checkpoint is located in *database/inference* (a template of the expected dataset columns is available at *resources/templates/FAIRS_predictions.csv*). 

- **logs:** log files are saved here

- **templates:** reference template files can be found here


**Environmental variables** are stored in the *app* folder (within the project folder). For security reasons, this file is typically not uploaded to GitHub. Instead, you must create this file manually by copying the template from *resources/templates/.env* and placing it in the *app* directory.

| Variable              | Description                                      |
|-----------------------|--------------------------------------------------|
| KERAS_BACKEND         | Sets the backend for Keras, default is PyTorch   |
| TF_CPP_MIN_LOG_LEVEL  | TensorFlow logging verbosity                     |
| MPLBACKEND            | Matplotlib backend, keep default as Agg          |

## 5. License
This project is licensed under the terms of the MIT license. See the LICENSE file for details.

## Disclaimer
This project is for educational purposes only. It should not be used as a way to make easy money, since the model won't be able to accurately forecast numbers merely based on previous observations!