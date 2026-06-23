from __future__ import annotations

import shutil
from typing import Any

from keras import Model

from server.common.checkpoints import (
    normalize_checkpoint_identifier,
    resolve_checkpoint_path,
)
from server.repositories.serialization.model import ModelSerializer

###############################################################################
def get_last_history_value(values: Any) -> float | None:
    if isinstance(values, list) and values:
        last_value = values[-1]
        if isinstance(last_value, (int, float)):
            return float(last_value)
    return None

###############################################################################
class CheckpointService:

    # -------------------------------------------------------------------------
    def __init__(self, model_serializer: ModelSerializer | None = None) -> None:
        self.model_serializer = model_serializer or ModelSerializer()

    # -------------------------------------------------------------------------
    def list_checkpoints(self) -> list[str]:
        return self.model_serializer.scan_checkpoints_folder()

    # -------------------------------------------------------------------------
    def resolve_existing_checkpoint(self, checkpoint_name: str) -> tuple[str, str]:
        normalized = normalize_checkpoint_identifier(checkpoint_name)
        checkpoint_path = resolve_checkpoint_path(normalized)
        available = set(self.list_checkpoints())
        if normalized not in available or not checkpoint_path.is_dir():
            raise FileNotFoundError(f"Checkpoint not found: {normalized}")
        return normalized, str(checkpoint_path)

    # -------------------------------------------------------------------------
    def get_metadata(self, checkpoint_name: str) -> dict[str, Any]:
        checkpoint, checkpoint_path = self.resolve_existing_checkpoint(checkpoint_name)
        configuration, session = self.model_serializer.load_training_configuration(
            checkpoint_path
        )
        history = session.get("history", {}) if isinstance(session, dict) else {}
        summary = {
            "dataset_id": configuration.get("dataset_id") or "",
            "sample_size": configuration.get("sample_size"),
            "seed": configuration.get("seed"),
            "episodes": configuration.get("episodes") or session.get("total_episodes"),
            "batch_size": configuration.get("batch_size"),
            "learning_rate": configuration.get("learning_rate"),
            "perceptive_field_size": configuration.get("perceptive_field_size"),
            "neurons": configuration.get("qnet_neurons"),
            "embedding_dimensions": configuration.get("embedding_dimensions"),
            "exploration_rate": configuration.get("exploration_rate"),
            "exploration_rate_decay": configuration.get("exploration_rate_decay"),
            "discount_rate": configuration.get("discount_rate"),
            "model_update_frequency": configuration.get("model_update_frequency"),
            "bet_amount": configuration.get("bet_amount"),
            "initial_capital": configuration.get("initial_capital"),
            "final_loss": get_last_history_value(history.get("loss")),
            "final_rmse": get_last_history_value(history.get("metrics")),
            "final_val_loss": get_last_history_value(history.get("val_loss")),
            "final_val_rmse": get_last_history_value(history.get("val_rmse")),
        }
        return {"checkpoint": checkpoint, "summary": summary}

    # -------------------------------------------------------------------------
    def load_checkpoint(
        self, checkpoint_name: str
    ) -> tuple[Model | Any, dict[str, Any], dict[str, Any], str]:
        normalized = normalize_checkpoint_identifier(checkpoint_name)
        return self.model_serializer.load_checkpoint(normalized)

    # -------------------------------------------------------------------------
    def load_training_configuration(
        self, checkpoint_path: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.model_serializer.load_training_configuration(checkpoint_path)

    # -------------------------------------------------------------------------
    def load_strategy_model(
        self, checkpoint_path: str, required: bool = False
    ) -> Model | Any | None:
        return self.model_serializer.load_strategy_model(checkpoint_path, required=required)

    # -------------------------------------------------------------------------
    def delete_checkpoint(self, checkpoint_name: str) -> None:
        _, checkpoint_path = self.resolve_existing_checkpoint(checkpoint_name)
        shutil.rmtree(checkpoint_path)
