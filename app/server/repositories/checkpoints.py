from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from keras import Model
from keras.models import load_model
from pydantic import ValidationError

from server.common import path as shared_paths
from server.common.checkpoints import normalize_checkpoint_identifier
from server.common.utils.logger import logger
from server.contracts.training import CheckpointConfiguration
from server.learning import models as custom_layers_registry  # noqa: F401


###############################################################################
class CheckpointRepository:
    """Own the checkpoint filesystem and validate its current file contract."""

    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        self.model_name = "FAIRS"
        self.strategy_model_file = shared_paths.CHECKPOINT_STRATEGY_MODEL_FILE_NAME

    # -------------------------------------------------------------------------
    def create_checkpoint_folder(self, checkpoint_name: str | None = None) -> str:
        selected_name = (
            checkpoint_name.strip() if isinstance(checkpoint_name, str) else ""
        )
        selected_name = re.sub(r"[\\/]+", "_", selected_name)
        if selected_name:
            selected_name = normalize_checkpoint_identifier(selected_name)
            checkpoint_path = shared_paths.checkpoint_directory(selected_name)
            if checkpoint_path.exists():
                raise ValueError(f"Checkpoint already exists: {selected_name}")
        else:
            today_datetime = datetime.now().strftime("%Y%m%dT%H%M%S")
            checkpoint_path = shared_paths.checkpoint_directory(
                f"{self.model_name}_{today_datetime}"
            )

        checkpoint_path.mkdir(parents=True, exist_ok=False)
        shared_paths.checkpoint_configuration_dir(checkpoint_path).mkdir(exist_ok=True)
        logger.debug("Created checkpoint folder at %s", checkpoint_path)
        return str(checkpoint_path)

    # -------------------------------------------------------------------------
    def create_checkpoint_workspace(
        self, checkpoint_name: str | None = None
    ) -> tuple[str, str]:
        """Reserve a checkpoint name and return final and private staging paths."""
        selected_name = (
            checkpoint_name.strip() if isinstance(checkpoint_name, str) else ""
        )
        selected_name = re.sub(r"[\\/]+", "_", selected_name)
        if selected_name:
            selected_name = normalize_checkpoint_identifier(selected_name)
        else:
            selected_name = f"{self.model_name}_{datetime.now():%Y%m%dT%H%M%S%f}"

        final_path = shared_paths.checkpoint_directory(selected_name)
        if final_path.exists():
            raise ValueError(f"Checkpoint already exists: {selected_name}")

        staging_path = final_path.parent / (
            f".{final_path.name}.staging-{uuid.uuid4().hex}"
        )
        staging_path.mkdir(parents=True, exist_ok=False)
        shared_paths.checkpoint_configuration_dir(staging_path).mkdir(exist_ok=True)
        logger.debug("Created checkpoint staging workspace at %s", staging_path)
        return str(final_path), str(staging_path)

    # -------------------------------------------------------------------------
    def create_resume_workspace(self, checkpoint_path: str) -> str:
        """Copy an existing checkpoint into an isolated workspace for resume."""
        source = shared_paths.as_path(checkpoint_path)
        staging_path = source.parent / f".{source.name}.staging-{uuid.uuid4().hex}"
        try:
            shutil.copytree(
                source,
                staging_path,
                ignore=shutil.ignore_patterns(
                    ".staging-*", ".backup-*", ".publish-*"
                ),
            )
        except Exception:
            if staging_path.exists():
                try:
                    shutil.rmtree(staging_path)
                except OSError:
                    logger.exception(
                        "Failed to remove partial resume workspace %s", staging_path
                    )
            raise
        return str(staging_path)

    # -------------------------------------------------------------------------
    @staticmethod
    def remove_staging_workspace(staging_path: str | None) -> None:
        if not staging_path:
            return
        path = shared_paths.as_path(staging_path)
        if not path.exists():
            return
        try:
            shutil.rmtree(path)
        except OSError:
            logger.exception("Failed to remove checkpoint staging workspace %s", path)

    # -------------------------------------------------------------------------
    def cleanup_incomplete_workspaces(self) -> None:
        """Remove hidden workspaces left by a force-terminated worker."""
        root = shared_paths.CHECKPOINT_PATH
        if not root.exists():
            return
        for entry in root.iterdir():
            if not entry.is_dir() or not (
                ".staging-" in entry.name
                or ".backup-" in entry.name
                or ".publish-" in entry.name
            ):
                continue
            try:
                shutil.rmtree(entry)
            except OSError:
                logger.exception("Failed to remove incomplete checkpoint workspace %s", entry)

    # -------------------------------------------------------------------------
    def publish_checkpoint(self, staging_path: str, final_path: str) -> None:
        """Publish a complete staging tree while preserving a prior checkpoint."""
        staging = shared_paths.as_path(staging_path)
        final = shared_paths.as_path(final_path)
        required_files = (
            shared_paths.checkpoint_saved_model_file(staging),
            shared_paths.checkpoint_configuration_file(staging),
            shared_paths.checkpoint_session_history_file(staging),
        )
        if not all(path.is_file() for path in required_files):
            raise ValueError(f"Checkpoint staging workspace is incomplete: {staging}")

        complete_path = staging / shared_paths.CHECKPOINT_COMPLETE_FILE_NAME
        self._write_text_atomically(complete_path, "complete\n")
        backup: Path | None = None
        try:
            if final.exists():
                backup = final.parent / f".{final.name}.backup-{uuid.uuid4().hex}"
                final.rename(backup)
            staging.rename(final)
        except Exception:
            if backup is not None and backup.exists() and not final.exists():
                backup.rename(final)
            raise
        finally:
            if backup is not None and backup.exists():
                try:
                    shutil.rmtree(backup)
                except OSError:
                    logger.exception("Failed to remove checkpoint backup %s", backup)

    # -------------------------------------------------------------------------
    @staticmethod
    def _write_text_atomically(path: Path, content: str) -> None:
        temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary_path.write_text(content, encoding="utf-8")
            temporary_path.replace(path)
        finally:
            if temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    logger.exception("Failed to remove temporary checkpoint file %s", temporary_path)

    # -------------------------------------------------------------------------
    def save_pretrained_model(self, model: Model, path: str) -> None:
        checkpoint_path = shared_paths.as_path(path)
        model_files_path = shared_paths.checkpoint_saved_model_file(checkpoint_path)
        temporary_path = model_files_path.with_name(
            f".{model_files_path.name}.{uuid.uuid4().hex}.tmp.keras"
        )
        try:
            model.save(temporary_path)
            temporary_path.replace(model_files_path)
        finally:
            if temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    logger.exception("Failed to remove temporary checkpoint model %s", temporary_path)
        logger.info(
            "Training session is over. Model %s has been saved",
            checkpoint_path.name,
        )

    # -------------------------------------------------------------------------
    def save_strategy_model(self, model: Model, path: str) -> None:
        checkpoint_path = shared_paths.as_path(path)
        model_file_path = shared_paths.checkpoint_strategy_model_file(
            checkpoint_path,
            self.strategy_model_file,
        )
        temporary_path = model_file_path.with_name(
            f".{model_file_path.name}.{uuid.uuid4().hex}.tmp.keras"
        )
        try:
            model.save(temporary_path)
            temporary_path.replace(model_file_path)
        finally:
            if temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    logger.exception("Failed to remove temporary strategy model %s", temporary_path)
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
        checkpoint_path = shared_paths.as_path(path)
        config_path = shared_paths.checkpoint_configuration_file(checkpoint_path)
        history_path = shared_paths.checkpoint_session_history_file(checkpoint_path)
        validated_configuration = CheckpointConfiguration.model_validate(configuration)

        self._write_text_atomically(
            config_path,
            json.dumps(validated_configuration.model_dump()),
        )
        self._write_text_atomically(history_path, json.dumps(history))

        logger.debug(
            "Model configuration, session history and metadata saved for %s",
            checkpoint_path.name,
        )

    # -------------------------------------------------------------------------
    def load_training_configuration(
        self,
        path: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        checkpoint_path = shared_paths.as_path(path)
        config_path = shared_paths.checkpoint_configuration_file(checkpoint_path)
        history_path = shared_paths.checkpoint_session_history_file(checkpoint_path)
        try:
            raw_configuration = json.loads(config_path.read_text(encoding="utf-8"))
            raw_history = json.loads(history_path.read_text(encoding="utf-8"))
            configuration = CheckpointConfiguration.model_validate(raw_configuration)
        except (OSError, json.JSONDecodeError, TypeError, ValidationError) as exc:
            raise ValueError(
                f"Checkpoint configuration is invalid: {config_path}"
            ) from exc
        if not isinstance(raw_history, dict):
            raise ValueError(f"Checkpoint history is invalid: {history_path}")
        return configuration.model_dump(), raw_history

    # -------------------------------------------------------------------------
    def scan_checkpoints_folder(self) -> list[str]:
        model_folders: list[str] = []
        if not shared_paths.CHECKPOINT_PATH.exists():
            shared_paths.CHECKPOINT_PATH.mkdir(parents=True, exist_ok=True)
            return model_folders

        for entry in shared_paths.CHECKPOINT_PATH.iterdir():
            if entry.name.startswith("."):
                continue
            if entry.is_dir() and all(
                path.is_file()
                for path in (
                    shared_paths.checkpoint_saved_model_file(entry),
                    shared_paths.checkpoint_configuration_file(entry),
                    shared_paths.checkpoint_session_history_file(entry),
                )
            ):
                model_folders.append(entry.name)

        return sorted(model_folders)

    # -------------------------------------------------------------------------
    def delete_checkpoint(self, checkpoint_path: str) -> None:
        path = shared_paths.as_path(checkpoint_path)
        shutil.rmtree(path)
        logger.debug("Deleted checkpoint folder at %s", path)

    # -------------------------------------------------------------------------
    def load_checkpoint(
        self,
        checkpoint: str,
    ) -> tuple[Model | Any, dict[str, Any], dict[str, Any], str]:
        checkpoint_path = shared_paths.checkpoint_directory(
            normalize_checkpoint_identifier(checkpoint)
        )
        configuration, session = self.load_training_configuration(str(checkpoint_path))
        model_path = shared_paths.checkpoint_saved_model_file(checkpoint_path)
        model = load_model(model_path)
        return model, configuration, session, str(checkpoint_path)

    # -------------------------------------------------------------------------
    def load_strategy_model(
        self,
        checkpoint_path: str,
        required: bool = False,
    ) -> Model | Any | None:
        model_path = shared_paths.checkpoint_strategy_model_file(
            checkpoint_path,
            self.strategy_model_file,
        )
        if not model_path.is_file():
            if required:
                raise FileNotFoundError(
                    f"Missing strategy model file: {self.strategy_model_file}"
                )
            return None
        return load_model(model_path)


__all__ = ["CheckpointRepository"]
