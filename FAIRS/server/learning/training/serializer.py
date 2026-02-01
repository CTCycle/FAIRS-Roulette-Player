from __future__ import annotations

from collections.abc import Callable
import json
import os
from datetime import datetime
from typing import Any

import pandas as pd
from keras import Model
from keras.models import load_model

from FAIRS.server.utils.constants import CHECKPOINT_PATH
from FAIRS.server.utils.logger import logger
from FAIRS.server.repositories.database import database
from FAIRS.server.utils.constants import ROULETTE_SERIES_TABLE
from FAIRS.server.services.process import RouletteSeriesEncoder
from FAIRS.server.learning.training.generator import RouletteSyntheticGenerator


###############################################################################
class DataSerializerExtension:
    def __init__(self) -> None:
        self.encoder = RouletteSeriesEncoder()

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
            dataset = self.encoder.encode(dataset)
            return dataset, True

        seed = configuration.get("seed", 42)
        sample_size = configuration.get("sample_size", 1.0)
        dataset_name = configuration.get("dataset_name")
        if isinstance(dataset_name, str):
            dataset_name = dataset_name.strip()
        if not dataset_name:
            dataset_name = None
        dataset = self.load_roulette_dataset(sample_size, seed, dataset_name)
        if dataset.empty or "extraction" not in dataset.columns:
            if dataset_name:
                raise ValueError(
                    f"No roulette dataset available for '{dataset_name}'."
                )
            raise ValueError("No roulette dataset available for training.")
        # Encoding is done at upload time - no need to encode again

        return dataset, False

    # -------------------------------------------------------------------------
    def load_roulette_dataset(
        self,
        sample_size: float = 1.0,
        seed: int = 42,
        dataset_name: str | None = None,
    ) -> pd.DataFrame:
        dataset = database.load_from_database(ROULETTE_SERIES_TABLE)
        if dataset.empty:
            return dataset
        if dataset_name and "dataset_name" in dataset.columns:
            dataset = dataset[dataset["dataset_name"] == dataset_name]
        if dataset.empty:
            return dataset
        if sample_size < 1.0:
            dataset = dataset.sample(frac=sample_size, random_state=seed)
        return dataset


###############################################################################
class ModelSerializer:
    def __init__(self) -> None:
        self.model_name = "FAIRS"

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

    # -------------------------------------------------------------------------
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

        with open(config_path, "w") as f:
            json.dump(configuration, f)

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
        if not os.path.exists(CHECKPOINT_PATH):
            os.makedirs(CHECKPOINT_PATH, exist_ok=True)
            return model_folders

        for entry in os.scandir(CHECKPOINT_PATH):
            if entry.is_dir():
                has_keras = any(
                    f.name.endswith(".keras") and f.is_file()
                    for f in os.scandir(entry.path)
                )
                if has_keras:
                    model_folders.append(entry.name)

        return model_folders

    # -------------------------------------------------------------------------
    def load_checkpoint(self, checkpoint: str) -> tuple[Model | Any, dict, dict, str]:
        checkpoint_path = os.path.join(CHECKPOINT_PATH, checkpoint)
        model_path = os.path.join(checkpoint_path, "saved_model.keras")
        model = load_model(model_path)
        configuration, session = self.load_training_configuration(checkpoint_path)

        return model, configuration, session, checkpoint_path
