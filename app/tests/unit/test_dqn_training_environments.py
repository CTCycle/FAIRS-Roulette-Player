from __future__ import annotations

import pandas as pd
import pytest

from server.learning.training.fitting import DQNTraining


def build_configuration(**overrides: object) -> dict[str, object]:
    configuration: dict[str, object] = {
        "training_seed": 7,
        "batch_size": 8,
        "model_update_frequency": 10,
        "replay_buffer_size": 20,
        "max_memory_size": 100,
        "perceptive_field_size": 8,
        "max_steps_episode": 100,
        "initial_capital": 100,
        "bet_amount": 1,
        "validation_size": 0.2,
    }
    configuration.update(overrides)
    return configuration


###############################################################################
def test_training_and_resume_share_validation_environment_builder() -> None:
    trainer = DQNTraining(build_configuration())
    data = pd.DataFrame({"extraction": [index % 37 for index in range(100)]})

    training_environment, validation_environment, state_size = trainer._build_environments(
        data,
        "checkpoint",
    )

    assert state_size == 8
    assert len(training_environment.extractions) == 80
    assert validation_environment is not None
    assert len(validation_environment.extractions) == 20


###############################################################################
def test_validation_partition_must_support_perceptive_window() -> None:
    trainer = DQNTraining(build_configuration(perceptive_field_size=16, validation_size=0.1))
    data = pd.DataFrame({"extraction": [index % 37 for index in range(100)]})

    with pytest.raises(ValueError, match="Validation partition"):
        trainer._build_environments(data, "checkpoint")


###############################################################################
def test_latest_stats_does_not_carry_sparse_validation_metrics_forward() -> None:
    trainer = DQNTraining(build_configuration())
    trainer.session_stats["val_loss"] = [0.4]
    trainer.session_stats["val_rmse"] = [0.5]
    trainer.session_stats["img_reward"] = [3.0]
    trainer.latest_metric_state.update(
        {"val_loss": None, "val_rmse": None, "val_reward": None}
    )

    latest_stats = trainer.get_latest_stats(0, 1, training_ready=True)

    assert latest_stats["val_loss"] is None
    assert latest_stats["val_rmse"] is None
    assert latest_stats["val_reward"] is None
