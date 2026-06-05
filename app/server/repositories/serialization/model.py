from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from keras import Model
from keras.models import load_model

from server.learning import models as custom_layers_registry  # noqa: F401
from server.common.path import CHECKPOINT_PATH
from server.common.utils.logger import logger


###############################################################################
class ModelSerializer:
    def __init__(self) -> None:
        self.model_name = "FAIRS"
        self.strategy_model_file = "strategy.keras"

    # -------------------------------------------------------------------------
    def create_checkpoint_folder(self, checkpoint_name: str | None = None) -> str:
        selected_name = (
            checkpoint_name.strip() if isinstance(checkpoint_name, str) else ""
        )
        selected_name = re.sub(r"[\\/]+", "_", selected_name)
        if selected_name:
            checkpoint_path = CHECKPOINT_PATH / selected_name
            if checkpoint_path.exists():
                raise ValueError(f"Checkpoint already exists: {selected_name}")
        else:
            today_datetime = datetime.now().strftime("%Y%m%dT%H%M%S")
            checkpoint_path = CHECKPOINT_PATH / f"{self.model_name}_{today_datetime}"

        checkpoint_path.mkdir(parents=True, exist_ok=False)
        (checkpoint_path / "configuration").mkdir(exist_ok=True)
        logger.debug(f"Created checkpoint folder at {checkpoint_path}")
        return str(checkpoint_path)

    # -------------------------------------------------------------------------
    def save_pretrained_model(self, model: Model, path: str) -> None:
        checkpoint_path = Path(path)
        model_files_path = checkpoint_path / "saved_model.keras"
        model.save(model_files_path)
        logger.info(
            f"Training session is over. Model {checkpoint_path.name} has been saved"
        )

    # -------------------------------------------------------------------------
    def save_strategy_model(self, model: Model, path: str) -> None:
        checkpoint_path = Path(path)
        model_file_path = checkpoint_path / self.strategy_model_file
        model.save(model_file_path)
        logger.info(
            "Training session is over. Strategy model %s has been saved",
            checkpoint_path.name,
        )

    # -------------------------------------------------------------------------
    def save_training_configuration(
        self,
        path: str,
        history: dict[str, Any],
        configuration: dict[str, Any],
    ) -> None:
        checkpoint_path = Path(path)
        config_path = checkpoint_path / "configuration" / "configuration.json"
        history_path = checkpoint_path / "configuration" / "session_history.json"

        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(configuration, file)

        with open(history_path, "w", encoding="utf-8") as file:
            json.dump(history, file)

        logger.debug(
            "Model configuration, session history and metadata saved for %s",
            checkpoint_path.name,
        )

    # -------------------------------------------------------------------------
    def load_training_configuration(
        self, path: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        checkpoint_path = Path(path)
        config_path = checkpoint_path / "configuration" / "configuration.json"
        history_path = checkpoint_path / "configuration" / "session_history.json"
        with open(config_path, encoding="utf-8") as file:
            configuration = json.load(file)
        with open(history_path, encoding="utf-8") as file:
            history = json.load(file)
        return configuration, history

    # -------------------------------------------------------------------------
    def scan_checkpoints_folder(self) -> list[str]:
        model_folders: list[str] = []
        if not CHECKPOINT_PATH.exists():
            CHECKPOINT_PATH.mkdir(parents=True, exist_ok=True)
            return model_folders

        for entry in CHECKPOINT_PATH.iterdir():
            if entry.is_dir() and any(
                file.suffix == ".keras" and file.is_file() for file in entry.iterdir()
            ):
                model_folders.append(entry.name)

        return model_folders

    # -------------------------------------------------------------------------
    def load_checkpoint(
        self, checkpoint: str
    ) -> tuple[Model | Any, dict[str, Any], dict[str, Any], str]:
        checkpoint_path = CHECKPOINT_PATH / checkpoint
        model_path = checkpoint_path / "saved_model.keras"
        model = load_model(model_path)
        configuration, session = self.load_training_configuration(str(checkpoint_path))
        return model, configuration, session, str(checkpoint_path)

    # -------------------------------------------------------------------------
    def load_strategy_model(
        self, checkpoint_path: str, required: bool = False
    ) -> Model | Any | None:
        model_path = Path(checkpoint_path) / self.strategy_model_file
        if not model_path.is_file():
            if required:
                raise FileNotFoundError(
                    f"Missing strategy model file: {self.strategy_model_file}"
                )
            return None
        return load_model(model_path)
