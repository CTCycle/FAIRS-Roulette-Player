# FAIRS: Fabulous Automated Intelligent Roulette System

## 1. Introduction
FAIRS is a research project dedicated to predicting upcoming outcomes in online roulette through a Deep Q-Network (DQN) agent. Instead of relying solely on immediate, isolated results, FAIRS utilizes sequences of past roulette spins, incorporating a perceptive field of historical outcomes as input. This approach allows the model to detect temporal patterns that might influence future events. Additionally, random number generation can be used to simulate a genuinely unpredictable game environment, mirroring the behavior of a real roulette wheel.

During training, the DQN agent learns to identify patterns within these sequences, and to select the actions associated with the highest Q-scores-signals of potentially more rewarding decisions. In doing so, FAIRS adapts sequence modeling techniques to the inherently random and structured nature of roulette outcomes, aiming to refine predictive accuracy in an environment defined by uncertainty.

> **Work in Progress**: This project is still under active development. It will be updated regularly, but please be aware that you may encounter bugs, issues, or incomplete features as we refine the codebase.

## 2. FAIRSnet model
FAIRSnet is a specialized neural network designed for roulette prediction within reinforcement learning contexts. Its core objective is forecasting the action most likely to yield the highest reward by analyzing the current state of the game, represented by a predefined series of recent outcomes (the perceived field). The model learns through interactions with the roulette environment, exploring multiple strategic betting options, including:

- Betting on a specific number (0-36)
- Betting on color outcomes (red or black)
- Betting on numerical ranges (high or low)
- Betting on specific dozen ranges
- Choosing to abstain from betting and exit the game

While roulette outcomes are theoretically random, some online platforms may use algorithms that exhibit patterns or slight autoregressive tendencies. The model is trained on a dataset built from past experiences, using reinforcement learning to optimize decision-making through DQN policy. The Q-Network head predicts Q-values that represents the confidence level for each possible outcome (suggested action). The model is trained using the Mean Squared Error (MSE) loss function, while tracking RMSE during training.

The application currently ships with the following functional blocks:

- **Dataset ingestion:** CSV/XLSX sources are imported into the embedded SQLite database from the Data Prep page.
- **Training services:** The training pipeline supports synthetic data generation, dataset sampling/shuffling, and checkpointed DQN training with live WebSocket updates.
- **Inference sessions:** Load any stored checkpoint, upload an inference context, and run a step-by-step roulette session that logs predictions.
- **Database browser:** Inspect stored roulette series, inference contexts, predicted games, and checkpoint summaries in the Database tab.

## 3. Installation
The project targets Windows 10/11 and requires roughly 2 GB of free disk space for the embedded Python runtime, dependencies, checkpoints, and datasets. A CUDA-capable NVIDIA GPU is recommended but not mandatory.

1. **Download the project**: clone the repository or extract the release archive into a writable location (avoid paths that require admin privileges).
2. **Configure environment variables (optional)**: copy `FAIRS/resources/templates/.env` into `FAIRS/settings/.env` and add overrides such as host/port values if needed.
3. **Run `start_on_windows.bat`**: the bootstrapper installs portable Python 3.12 and Node.js runtimes, downloads Astral's `uv`, syncs dependencies from `pyproject.toml`, then launches the backend (FastAPI) and frontend (Vite preview). The script is idempotent - rerun it any time to repair the environment or re-open the app.

Running the script the first time can take several minutes depending on bandwidth. Subsequent runs reuse the cached Python runtime and only re-sync packages when `pyproject.toml` changes.

### 4.1 Just-In-Time (JIT) Compiler
`torch.compile` can be enabled via `FAIRS/settings/server_configurations.json` (`device.jit_compile`). When enabled, TorchInductor optimizes the computation graph for compatible devices. Triton is bundled automatically so no separate CUDA toolkit installation is required.

### 4.2 Manual or developer installation
If you prefer managing Python yourself (for debugging or CI):

1. Install Python 3.12.x and `uv` (https://github.com/astral-sh/uv).
2. From the repository root run `uv sync` to create a virtual environment with the versions pinned in `pyproject.toml`.
3. Copy `.env` as described earlier if you need to override host/port values.
4. Launch the backend with `uv run python -m uvicorn FAIRS.server.app:app`.
5. In `FAIRS/client`, run `npm install` followed by `npm run build` and `npm run preview`.

## 5. How to use
Launch the application by double-clicking `start_on_windows.bat`. On startup the UI connects to the FastAPI backend and uses WebSockets for live training updates.

1. **Prepare data**: upload a CSV/XLSX dataset in the Data Prep tab (stored in the embedded SQLite database).
2. **Train**: configure a new training run or resume a checkpoint in the Training tab.
3. **Run inference**: upload an inference context, select a checkpoint, and step through predictions in the Inference tab.
4. **Inspect data**: use the Database tab to browse stored tables and metadata.

On Windows, run `start_on_windows.bat` to launch the application. Please note that some antivirus software, such as Avast, may flag or quarantine python.exe when called by the .bat file. If you encounter unusual behavior, consider adding an exception in your antivirus settings.

The main interface streamlines navigation across the application's core services: dataset preparation, model training, inference, and database browsing. Model training supports customizable configurations and resuming from pretrained checkpoints.

**Data Prep tab:**
- Upload CSV/XLSX roulette series into the embedded database.
- Review upload status and confirm the dataset name that will be available for training.

![dataset_prep](FAIRS/assets/figures/dataset_prep.png)

**Training tab:**
- Configure agent, dataset, session, and checkpoint options for a new run.
- Resume from an existing checkpoint with additional episodes.
- Track loss/RMSE, rewards, capital, and progress from the live dashboard.

![training_page](FAIRS/assets/figures/training_page.png)

**Inference tab:**
- Upload an inference context, select a checkpoint, and start a session.
- Submit real extractions to receive the next prediction and track capital.


![inference_page](FAIRS/assets/figures/inference_page.png)


**Database tab:**
- Browse stored tables with pagination and quick stats (columns/rows).

![database_browser](FAIRS/assets/figures/database_browser.png)

### 5.1 Setup and Maintenance
`setup_and_maintenance.bat` launches a lightweight maintenance console with these options:

- **Remove logs**: clears `resources/logs` to save disk space or to reset diagnostics before a new run.
- **Uninstall app**: removes local runtimes, caches, and frontend artifacts.
- **Initialize database**: runs the server-side initialization script.


### 5.2 Resources
This folder organizes data and results across training, inference, and runtime setup. By default, all data is stored within an SQLite database; an external DB can be configured via `FAIRS/settings/server_configurations.json`. The directory structure includes:

- **checkpoints:**  pretrained model checkpoints are stored here, and can be used either for resuming training or performing inference with an already trained model.

- **database:** embedded SQLite database (`sqlite.db`) containing roulette series, inference contexts, predicted games, and checkpoint summaries.

- **logs:** application log files.

- **runtimes:** portable Python/Node.js runtimes installed by `start_on_windows.bat`.

- **templates:** reference template files (including the `.env` starter).

Environmental variables reside in `FAIRS/settings/.env`. Copy the template from `resources/templates/.env` and adjust as needed:

| Variable      | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| FASTAPI_HOST  | Backend host for the FastAPI server (used by the launcher).                |
| FASTAPI_PORT  | Backend port for the FastAPI server (used by the launcher).                |
| UI_HOST       | Frontend host for the Vite preview server.                                 |
| UI_PORT       | Frontend port for the Vite preview server.                                 |
| RELOAD        | Set to `true` to enable auto-reload for the backend.                       |
| MPLBACKEND    | Matplotlib backend; `Agg` keeps plotting headless for worker threads.      |

## 6. License
This project is licensed under the terms of the MIT license. See the LICENSE file for details.

## Disclaimer
This project is for educational purposes only. It should not be used as a way to make easy money, since the model won't be able to accurately forecast numbers merely based on previous observations!
