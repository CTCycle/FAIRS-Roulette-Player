from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

from keras import Model
from keras.models import load_model

from FAIRS.server.learning import models as custom_layers_registry  # noqa: F401
from FAIRS.server.common.constants import CHECKPOINT_PATH
from FAIRS.server.common.utils.logger import logger


###############################################################################
class ModelSerializer:
    def __init__(self) -> None:
        self.model_name = "FAIRS"

    # -------------------------------------------------------------------------
    def create_checkpoint_folder(self, checkpoint_name: str | None = None) -> str:
        selected_name = (
            checkpoint_name.strip() if isinstance(checkpoint_name, str) else ""
        )
        selected_name = re.sub(r"[\\/]+", "_", selected_name)
        if selected_name:
            checkpoint_path = os.path.join(CHECKPOINT_PATH, selected_name)
            if os.path.exists(checkpoint_path):
                raise ValueError(f"Checkpoint already exists: {selected_name}")
        else:
            today_datetime = datetime.now().strftime("%Y%m%dT%H%M%S")
            checkpoint_path = os.path.join(
                CHECKPOINT_PATH,
                f"{self.model_name}_{today_datetime}",
            )

        os.makedirs(checkpoint_path, exist_ok=False)
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
        self,
        path: str,
        history: dict[str, Any],
        configuration: dict[str, Any],
    ) -> None:
        config_path = os.path.join(path, "configuration", "configuration.json")
        history_path = os.path.join(path, "configuration", "session_history.json")

        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(configuration, file)

        with open(history_path, "w", encoding="utf-8") as file:
            json.dump(history, file)

        logger.debug(
            "Model configuration, session history and metadata saved for %s",
            os.path.basename(path),
        )

    # -------------------------------------------------------------------------
    def load_training_configuration(self, path: str) -> tuple[dict[str, Any], dict[str, Any]]:
        config_path = os.path.join(path, "configuration", "configuration.json")
        history_path = os.path.join(path, "configuration", "session_history.json")
        with open(config_path, encoding="utf-8") as file:
            configuration = json.load(file)
        with open(history_path, encoding="utf-8") as file:
            history = json.load(file)
        return configuration, history

    # -------------------------------------------------------------------------
    def scan_checkpoints_folder(self) -> list[str]:
        model_folders: list[str] = []
        if not os.path.exists(CHECKPOINT_PATH):
            os.makedirs(CHECKPOINT_PATH, exist_ok=True)
            return model_folders

        for entry in os.scandir(CHECKPOINT_PATH):
            if entry.is_dir():
                has_keras = any(
                    file.name.endswith(".keras") and file.is_file()
                    for file in os.scandir(entry.path)
                )
                if has_keras:
                    model_folders.append(entry.name)

        return model_folders

    # -------------------------------------------------------------------------
    def load_checkpoint(self, checkpoint: str) -> tuple[Model | Any, dict[str, Any], dict[str, Any], str]:
        checkpoint_path = os.path.join(CHECKPOINT_PATH, checkpoint)
        model_path = os.path.join(checkpoint_path, "saved_model.keras")
        model = load_model(model_path)
        configuration, session = self.load_training_configuration(checkpoint_path)
        return model, configuration, session, checkpoint_path
