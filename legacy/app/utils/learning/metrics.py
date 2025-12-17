from __future__ import annotations

from typing import Any

import keras
import tensorflow as tf


# [LOSS FUNCTION]
###############################################################################
class RouletteCategoricalCrossentropy(keras.losses.Loss):
    def __init__(
        self,
        name="RouletteCategoricalCrossentropy",
        penalty_increase=0.05,
        perceptive_field=10,
        **kwargs,
    ) -> None:
        super(RouletteCategoricalCrossentropy, self).__init__(name=name, **kwargs)
        self.penalty_increase = penalty_increase
        self.perceptive_size = perceptive_field
        # Define penalty_scores as per the increasing factor
        self.penalty_scores = [
            1 + (i - 1) * self.penalty_increase
            for i in range(1, self.perceptive_size + 1)
        ]
        self.penalty_scores = keras.ops.convert_to_tensor(
            self.penalty_scores, dtype=tf.float32
        )
        # Use reduction='none' to get per-sample loss
        self.loss = keras.losses.SparseCategoricalCrossentropy(
            from_logits=False, reduction="none"
        )

    # -------------------------------------------------------------------------
    def call(self, y_true: Any, y_pred: Any) -> Any:
        loss = self.loss(y_true, y_pred)
        # Apply penalty based on the difference between prediction and true value
        total_loss = loss * self.penalty_scores
        total_loss = keras.ops.mean(total_loss)

        return total_loss

    # -------------------------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        base_config = super(RouletteCategoricalCrossentropy, self).get_config()
        return {
            **base_config,
            "name": self.name,
            "perceptive_field": self.perceptive_size,
            "penalty_increase": self.penalty_increase,
        }

    @classmethod
    def from_config(
        cls: type[RouletteCategoricalCrossentropy],
        config: dict[str, Any],
    ) -> RouletteCategoricalCrossentropy:
        return cls(**config)


# [METRICS]
###############################################################################
class RouletteAccuracy(keras.metrics.Metric):
    def __init__(self, name: str = "RouletteAccuracy", **kwargs) -> None:
        super(RouletteAccuracy, self).__init__(name=name, **kwargs)
        self.total = self.add_weight(name="total", initializer="zeros")
        self.count = self.add_weight(name="count", initializer="zeros")

    # -------------------------------------------------------------------------
    def update_state(
        self, y_true: Any, y_pred: Any, sample_weight: Any | None = None
    ) -> None:
        y_true = keras.ops.cast(y_true, dtype=keras.config.floatx())
        probabilities = keras.ops.argmax(y_pred, axis=1)
        accuracy = keras.ops.equal(y_true, probabilities)

        if sample_weight is not None:
            sample_weight = keras.ops.cast(sample_weight, dtype=keras.config.floatx())
            accuracy = keras.ops.multiply(accuracy, sample_weight)

        # Update the state variables
        self.total.assign_add(keras.ops.sum(accuracy))

    # -------------------------------------------------------------------------
    def result(self) -> Any:
        return self.total / (self.count + keras.backend.epsilon())

    # -------------------------------------------------------------------------
    def reset_NUMBERS(self) -> None:
        self.total.assign(0)
        self.count.assign(0)

    # -------------------------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        base_config = super(RouletteAccuracy, self).get_config()
        return {**base_config, "name": self.name}

    @classmethod
    def from_config(
        cls: type[RouletteAccuracy],
        config: dict[str, Any],
    ) -> RouletteAccuracy:
        return cls(**config)
