from __future__ import annotations

from typing import Any

import keras
from keras import activations, layers


###############################################################################
@keras.saving.register_keras_serializable(package="CustomLayers", name="AddNorm")
class AddNorm(keras.layers.Layer):
    supports_masking = True

    def __init__(self, epsilon: float = 10e-5, **kwargs) -> None:
        super(AddNorm, self).__init__(**kwargs)
        self.epsilon = epsilon
        self.add = layers.Add()
        self.layernorm = layers.LayerNormalization(epsilon=self.epsilon)

    # -------------------------------------------------------------------------
    def build(self, input_shape) -> None:
        self.add.build(input_shape)
        output_shape = self.add.compute_output_shape(input_shape)
        self.layernorm.build(output_shape)
        super(AddNorm, self).build(input_shape)

    # -------------------------------------------------------------------------
    def call(self, inputs) -> Any:
        x1, x2 = inputs
        x_add = self.add([x1, x2])
        x_norm = self.layernorm(x_add)
        return x_norm

    # -------------------------------------------------------------------------
    def get_config(self) -> dict[Any, Any]:
        config = super(AddNorm, self).get_config()
        config.update({"epsilon": self.epsilon})
        return config

    # -------------------------------------------------------------------------
    @classmethod
    def from_config(
        cls: type[AddNorm],
        config: dict[str, Any],
    ) -> AddNorm:
        return cls(**config)


###############################################################################
@keras.saving.register_keras_serializable(package="CustomLayers", name="QScoreNet")
class QScoreNet(keras.layers.Layer):
    supports_masking = True

    def __init__(self, dense_units: int, output_size: int, seed: int, **kwargs) -> None:
        super(QScoreNet, self).__init__(**kwargs)
        self.dense_units = dense_units
        self.output_size = output_size
        self.seed = seed
        self.flatten = layers.Flatten()
        self.Q1 = layers.Dense(self.dense_units, kernel_initializer="he_uniform")
        self.Q2 = layers.Dense(
            self.output_size,
            kernel_initializer="he_uniform",
            dtype=keras.config.floatx(),
        )
        self.batch_norm = layers.BatchNormalization()

    # -------------------------------------------------------------------------
    def build(self, input_shape) -> None:
        self.flatten.build(input_shape)
        flattened_shape = self.flatten.compute_output_shape(input_shape)
        self.Q1.build(flattened_shape)
        q1_shape = self.Q1.compute_output_shape(flattened_shape)
        self.batch_norm.build(q1_shape)
        self.Q2.build(q1_shape)
        super(QScoreNet, self).build(input_shape)

    # -------------------------------------------------------------------------
    def call(self, inputs, training: bool | None = None) -> Any:
        x = self.flatten(inputs)
        x = self.Q1(x)
        x = self.batch_norm(x, training=training)
        x = activations.relu(x)
        output = self.Q2(x)
        return output

    # -------------------------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        config = super(QScoreNet, self).get_config()
        config.update(
            {
                "dense_units": self.dense_units,
                "output_size": self.output_size,
                "seed": self.seed,
            }
        )
        return config

    # -------------------------------------------------------------------------
    @classmethod
    def from_config(
        cls: type[QScoreNet],
        config: dict[str, Any],
    ) -> QScoreNet:
        return cls(**config)


###############################################################################
@keras.saving.register_keras_serializable(package="CustomLayers", name="BatchNormDense")
class BatchNormDense(layers.Layer):
    supports_masking = True

    def __init__(self, units: int, **kwargs) -> None:
        super(BatchNormDense, self).__init__(**kwargs)
        self.units = units
        self.dense = layers.Dense(units, kernel_initializer="he_uniform")
        self.batch_norm = layers.BatchNormalization()

    # -------------------------------------------------------------------------
    def build(self, input_shape) -> None:
        self.dense.build(input_shape)
        dense_shape = self.dense.compute_output_shape(input_shape)
        self.batch_norm.build(dense_shape)
        super(BatchNormDense, self).build(input_shape)

    # -------------------------------------------------------------------------
    def call(self, inputs, training: bool | None = None) -> Any:
        layer = self.dense(inputs)
        layer = self.batch_norm(layer, training=training)
        layer = activations.relu(layer)
        return layer

    # -------------------------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        config = super(BatchNormDense, self).get_config()
        config.update({"units": self.units})
        return config

    # -------------------------------------------------------------------------
    @classmethod
    def from_config(
        cls: type[BatchNormDense],
        config: dict[str, Any],
    ) -> BatchNormDense:
        return cls(**config)
