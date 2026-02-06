from __future__ import annotations

from typing import Any

import keras
from keras import layers

from FAIRS.server.utils.constants import PAD_VALUE


###############################################################################
@keras.saving.register_keras_serializable(
    package="CustomLayers", name="RouletteEmbedding"
)
class RouletteEmbedding(keras.layers.Layer):
    def __init__(
        self,
        embedding_dims: int,
        numbers: int,
        mask_padding: bool = True,
        **kwargs: Any,
    ) -> None:
        super(RouletteEmbedding, self).__init__(**kwargs)
        self.embedding_dims = embedding_dims
        self.numbers = numbers
        self.mask_padding = mask_padding
        # mask_zero=False because we handle masking manually in _compute_mask_internal
        # and don't want Keras to propagate masks to downstream layers (Flatten doesn't support it)
        self.numbers_embedding = layers.Embedding(
            input_dim=self.numbers,
            output_dim=self.embedding_dims,
            mask_zero=False,
        )
        self.embedding_scale: Any = keras.ops.sqrt(self.embedding_dims)

    # -------------------------------------------------------------------------
    def build(self, input_shape: Any) -> None:
        self.numbers_embedding.build(input_shape)
        super(RouletteEmbedding, self).build(input_shape)

    # -------------------------------------------------------------------------
    def call(self, inputs: Any) -> Any:
        embedded_numbers = self.numbers_embedding(inputs)
        embedded_numbers *= self.embedding_scale

        if self.mask_padding:
            mask = self._compute_mask_internal(inputs)
            mask = keras.ops.expand_dims(
                keras.ops.cast(mask, keras.config.floatx()), axis=-1
            )
            embedded_numbers *= mask

        return embedded_numbers

    # -------------------------------------------------------------------------
    def compute_mask(self, inputs, previous_mask=None) -> Any:
        # Do not propagate mask to downstream layers (Flatten doesn't support it)
        # The mask is only used internally in call() to zero out padding
        return None

    # -------------------------------------------------------------------------
    def _compute_mask_internal(self, inputs) -> Any:
        """Internal method to compute mask for use in call()."""
        mask = keras.ops.not_equal(inputs, PAD_VALUE)
        return mask

    # -------------------------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        config = super(RouletteEmbedding, self).get_config()
        config.update(
            {
                "numbers": self.numbers,
                "embedding_dims": self.embedding_dims,
                "mask_padding": self.mask_padding,
            }
        )
        return config

    # -------------------------------------------------------------------------
    @classmethod
    def from_config(
        cls: type[RouletteEmbedding],
        config: dict[str, Any],
    ) -> RouletteEmbedding:
        return cls(**config)
