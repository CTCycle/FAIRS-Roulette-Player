from __future__ import annotations

import pandas as pd

from server.common.roulette import ROULETTE_RUNTIME_ATTR, encode_roulette_series
from server.contracts.configuration import RouletteSettings
from server.services.training_data import TrainingDataService

###############################################################################
def test_generated_training_series_matches_environment_contract() -> None:
    service = TrainingDataService(database_settings=None)

    dataset, synthetic = service.get_training_series(
        {
            "use_data_generator": True,
            "num_generated_samples": 100,
            "perceptive_field_size": 8,
            "max_steps_episode": 100,
            "seed": 42,
        }
    )

    assert synthetic is True
    assert len(dataset) == 100
    assert "extraction" in dataset.columns
    assert "wheel_position" in dataset.columns
    assert "color_code" in dataset.columns
    assert "outcome" not in dataset.columns
    assert dataset["extraction"].between(0, 36).all()

###############################################################################
def test_generated_training_series_respects_runtime_number_pool() -> None:
    service = TrainingDataService(database_settings=None)
    roulette_settings = RouletteSettings(
        minimum_number=0,
        maximum_number=8,
        exclude_zero=True,
        invert_colors=True,
        show_number_labels=False,
    )

    dataset, synthetic = service.get_training_series(
        {
            "use_data_generator": True,
            "num_generated_samples": 500,
            "perceptive_field_size": 8,
            "max_steps_episode": 100,
            "seed": 42,
        },
        roulette_settings,
    )

    assert synthetic is True
    assert dataset["extraction"].between(1, 8).all()
    assert 0 not in set(dataset["extraction"].tolist())
    assert dataset.attrs[ROULETTE_RUNTIME_ATTR] == {
        "minimum_number": 0,
        "maximum_number": 8,
        "exclude_zero": True,
        "invert_colors": True,
        "show_number_labels": False,
    }

###############################################################################
def test_roulette_encoding_isolated_from_input_frame() -> None:
    source = pd.DataFrame({"outcome": [0, 1, 32]})

    encoded = encode_roulette_series(source)

    assert list(source.columns) == ["outcome"]
    assert encoded["color_code"].notna().all()
    assert encoded["wheel_position"].notna().all()

###############################################################################
def test_training_subsample_preserves_contiguous_sequence_order() -> None:
    source = pd.DataFrame({"outcome": list(range(20))})

    sampled = TrainingDataService._sample_contiguous_window(source, 0.5, seed=7)
    repeated = TrainingDataService._sample_contiguous_window(source, 0.5, seed=7)

    assert len(sampled) == 10
    assert sampled["outcome"].diff().dropna().eq(1).all()
    pd.testing.assert_frame_equal(sampled, repeated)
