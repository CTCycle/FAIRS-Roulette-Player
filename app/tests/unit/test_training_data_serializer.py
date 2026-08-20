from __future__ import annotations

import pandas as pd

from server.common.roulette import encode_roulette_series
from server.learning.training.serializer import DataSerializerExtension

###############################################################################
def test_generated_training_series_matches_environment_contract() -> None:
    serializer = object.__new__(DataSerializerExtension)

    dataset, synthetic = serializer.get_training_series(
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


def test_roulette_encoding_isolated_from_input_frame() -> None:
    source = pd.DataFrame({"outcome": [0, 1, 32]})

    encoded = encode_roulette_series(source)

    assert list(source.columns) == ["outcome"]
    assert encoded["color_code"].notna().all()
    assert encoded["wheel_position"].notna().all()
