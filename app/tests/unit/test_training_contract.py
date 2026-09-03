from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.contracts.training import TrainingConfig


###############################################################################
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"exploration_rate": 0.1, "minimum_exploration_rate": 0.2},
            "minimum_exploration_rate must not exceed exploration_rate",
        ),
        (
            {"max_memory_size": 500, "replay_buffer_size": 600},
            "replay_buffer_size must not exceed max_memory_size",
        ),
        (
            {"batch_size": 256, "replay_buffer_size": 128},
            "batch_size must not exceed replay_buffer_size",
        ),
        (
            {"dynamic_betting_enabled": False, "bet_strategy_model_enabled": True},
            "bet_strategy_model_enabled requires dynamic_betting_enabled",
        ),
        (
            {
                "dynamic_betting_enabled": True,
                "bet_unit": 20,
                "bet_max": 10,
            },
            "bet_max must be greater than or equal to bet_unit",
        ),
    ],
)
def test_training_config_rejects_inconsistent_dqn_relationships(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        TrainingConfig(use_data_generator=True, **overrides)


###############################################################################
def test_training_config_accepts_consistent_replay_and_exploration_settings() -> None:
    config = TrainingConfig(
        use_data_generator=True,
        exploration_rate=0.5,
        minimum_exploration_rate=0.1,
        max_memory_size=2000,
        replay_buffer_size=1000,
        batch_size=64,
    )

    assert config.replay_buffer_size == 1000
    assert config.training_seed == 42
