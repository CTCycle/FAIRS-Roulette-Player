from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import pandas as pd
from keras import Model
from keras.models import load_model
from keras.utils import plot_model

from FAIRS.app.utils.constants import CHECKPOINT_PATH
from FAIRS.app.utils.logger import logger
from FAIRS.app.utils.repository.database import database
from FAIRS.app.utils.services.generator import RouletteSyntheticGenerator


# [DATA SERIALIZATION]
###############################################################################
class DataSerializer:
    def __init__(self) -> None:
        self.data_batch = 2000

    # -------------------------------------------------------------------------
    def generate_synthetic_dataset(self, configuration: dict[str, Any]) -> pd.DataFrame:
        generator = RouletteSyntheticGenerator(configuration)
        dataset = generator.generate()

        return dataset

    # -------------------------------------------------------------------------
    def get_training_series(
        self, configuration: dict[str, Any]
    ) -> tuple[pd.DataFrame, bool]:
        use_generator = configuration.get("use_data_generator", False)
        if use_generator:
            dataset = self.generate_synthetic_dataset(configuration)
            return dataset, True

        seed = configuration.get("seed", 42)
        sample_size = configuration.get("sample_size", 1.0)
        dataset = self.load_roulette_dataset(sample_size, seed)

        return dataset, False

    # -------------------------------------------------------------------------
    def load_roulette_dataset(
        self, sample_size: float = 1.0, seed: int = 42
    ) -> pd.DataFrame:
        dataset = database.load_from_database("ROULETTE_SERIES")
        if sample_size < 1.0:
            dataset = dataset.sample(frac=sample_size, random_state=seed)

        return dataset

    # -------------------------------------------------------------------------
    def load_inference_dataset(self) -> pd.DataFrame:
        dataset = database.load_from_database("PREDICTED_GAMES")
        return dataset

    # -------------------------------------------------------------------------
    def save_roulette_dataset(self, dataset: pd.DataFrame) -> None:
        database.save_into_database(dataset, "ROULETTE_SERIES")

    # -------------------------------------------------------------------------
    def save_predicted_games(self, dataset: pd.DataFrame) -> None:
        database.save_into_database(dataset, "PREDICTED_GAMES")

    # -------------------------------------------------------------------------
    def save_checkpoints_summary(self, data: pd.DataFrame) -> None:
        database.upsert_into_database(data, "CHECKPOINTS_SUMMARY")


# [MODEL SERIALIZATION]
###############################################################################
class ModelSerializer:
    def __init__(self) -> None:
        self.model_name = "FAIRS"

    # function to create a folder where to save model checkpoints
    # -------------------------------------------------------------------------
    def create_checkpoint_folder(self) -> str:
        today_datetime = datetime.now().strftime("%Y%m%dT%H%M%S")
        checkpoint_path = os.path.join(
            CHECKPOINT_PATH, f"{self.model_name}_{today_datetime}"
        )
        os.makedirs(checkpoint_path, exist_ok=True)
        os.makedirs(os.path.join(checkpoint_path, "configuration"), exist_ok=True)
        logger.debug(f"Created checkpoint folder at {checkpoint_path}")

        return checkpoint_path

    # ------------------------------------------------------------------------
    def save_pretrained_model(self, model: Model, path: str) -> None:
        model_files_path = os.path.join(path, "saved_model.keras")
        model.save(model_files_path)
        logger.info(
            f"Training session is over. Model {os.path.basename(path)} has been saved"
        )

    # -------------------------------------------------------------------------
    def save_training_configuration(
        self, path: str, history: dict, configuration: dict[str, Any]
    ) -> None:
        config_path = os.path.join(path, "configuration", "configuration.json")
        history_path = os.path.join(path, "configuration", "session_history.json")

        # Save training and model configuration
        with open(config_path, "w") as f:
            json.dump(configuration, f)

        # Save session history
        with open(history_path, "w") as f:
            json.dump(history, f)

        logger.debug(
            f"Model configuration, session history and metadata saved for {os.path.basename(path)}"
        )

    # -------------------------------------------------------------------------
    def load_training_configuration(self, path: str) -> tuple[dict, dict]:
        config_path = os.path.join(path, "configuration", "configuration.json")
        history_path = os.path.join(path, "configuration", "session_history.json")
        with open(config_path) as f:
            configuration = json.load(f)

        with open(history_path) as f:
            history = json.load(f)

        return configuration, history

    # -------------------------------------------------------------------------
    def scan_checkpoints_folder(self) -> list[str]:
        model_folders = []
        for entry in os.scandir(CHECKPOINT_PATH):
            if entry.is_dir():
                # Check if the folder contains at least one .keras file
                has_keras = any(
                    f.name.endswith(".keras") and f.is_file()
                    for f in os.scandir(entry.path)
                )
                if has_keras:
                    model_folders.append(entry.name)

        return model_folders

    # -------------------------------------------------------------------------
    def save_model_plot(self, model: Model, path: str) -> None:
        try:
            plot_path = os.path.join(path, "model_layout.png")
            plot_model(
                model,
                to_file=plot_path,
                show_shapes=True,
                show_layer_names=True,
                show_layer_activations=True,
                expand_nested=True,
                rankdir="TB",
                dpi=400,
            )
            logger.debug(f"Model architecture plot generated as {plot_path}")
        except (OSError, FileNotFoundError, ImportError):
            logger.warning(
                "Could not generate model architecture plot (graphviz/pydot not correctly installed)"
            )

    # -------------------------------------------------------------------------
    def load_checkpoint(self, checkpoint: str) -> tuple[Model | Any, dict, dict, str]:
        # effectively load the model using keras builtin method
        # load configuration data from .json file in checkpoint folder
        checkpoint_path = os.path.join(CHECKPOINT_PATH, checkpoint)
        model_path = os.path.join(checkpoint_path, "saved_model.keras")
        model = load_model(model_path)
        configuration, session = self.load_training_configuration(checkpoint_path)

        return model, configuration, session, checkpoint_path
