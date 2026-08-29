from __future__ import annotations

from typing import Any

from keras import Model

from server.common.checkpoints import (
    normalize_checkpoint_identifier,
    resolve_checkpoint_path,
)
from server.contracts.training import TrainingCheckpointSummary
from server.repositories.checkpoints import CheckpointRepository

###############################################################################
def get_last_history_value(values: Any) -> float | None:
    if isinstance(values, list) and values:
        last_value = values[-1]
        if isinstance(last_value, (int, float)):
            return float(last_value)
    return None

###############################################################################
class CheckpointReferenceError(RuntimeError):
    """Raised when dataset deletion would invalidate checkpoint metadata."""

###############################################################################
class CheckpointService:

    # -------------------------------------------------------------------------
    def __init__(
        self,
        checkpoint_repository: CheckpointRepository | None = None,
    ) -> None:
        self.checkpoint_repository = checkpoint_repository or CheckpointRepository()

    # -------------------------------------------------------------------------
    def list_checkpoints(self) -> list[str]:
        return self.checkpoint_repository.scan_checkpoints_folder()

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
        configuration, session = self.checkpoint_repository.load_training_configuration(
            checkpoint_path
        )
        history = session.get("history", {}) if isinstance(session, dict) else {}
        summary = TrainingCheckpointSummary.model_validate({
            "dataset_id": configuration.get("dataset_id"),
            "sample_size": configuration.get("sample_size"),
            "seed": configuration.get("seed"),
            "episodes": configuration["episodes"],
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
        })
        return {"checkpoint": checkpoint, "summary": summary.model_dump()}

    # -------------------------------------------------------------------------
    def find_dataset_references(self, dataset_id: int) -> list[str]:
        """Return checkpoints whose persisted configuration uses ``dataset_id``."""
        references: list[str] = []
        for checkpoint in self.list_checkpoints():
            try:
                _, checkpoint_path = self.resolve_existing_checkpoint(checkpoint)
                configuration, _ = self.checkpoint_repository.load_training_configuration(
                    checkpoint_path
                )
            except (OSError, TypeError, ValueError) as exc:
                raise CheckpointReferenceError(
                    f"Unable to inspect checkpoint '{checkpoint}' before deleting a dataset."
                ) from exc

            if not isinstance(configuration, dict):
                raise CheckpointReferenceError(
                    f"Unable to inspect checkpoint '{checkpoint}' before deleting a dataset."
                )
            reference = configuration.get("dataset_id")
            if reference is not None and (
                isinstance(reference, bool) or not isinstance(reference, int)
            ):
                raise CheckpointReferenceError(
                    f"Unable to inspect checkpoint '{checkpoint}' before deleting a dataset."
                )
            if reference == dataset_id:
                references.append(checkpoint)
        return references

    # -------------------------------------------------------------------------
    def load_checkpoint(
        self, checkpoint_name: str
    ) -> tuple[Model | Any, dict[str, Any], dict[str, Any], str]:
        normalized = normalize_checkpoint_identifier(checkpoint_name)
        return self.checkpoint_repository.load_checkpoint(normalized)

    # -------------------------------------------------------------------------
    def load_training_configuration(
        self, checkpoint_path: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.checkpoint_repository.load_training_configuration(checkpoint_path)

    # -------------------------------------------------------------------------
    def load_strategy_model(
        self, checkpoint_path: str, required: bool = False
    ) -> Model | Any | None:
        return self.checkpoint_repository.load_strategy_model(
            checkpoint_path, required=required
        )

    # -------------------------------------------------------------------------
    def delete_checkpoint(self, checkpoint_name: str) -> None:
        _, checkpoint_path = self.resolve_existing_checkpoint(checkpoint_name)
        self.checkpoint_repository.delete_checkpoint(checkpoint_path)
