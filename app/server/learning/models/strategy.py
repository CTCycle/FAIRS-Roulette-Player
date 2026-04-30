from __future__ import annotations

from typing import Any

from keras import Model, layers, losses, metrics, optimizers

from FAIRS.server.common.constants import NUMBERS
from FAIRS.server.learning.betting.types import STRATEGY_COUNT
from FAIRS.server.learning.models.embeddings import RouletteEmbedding
from FAIRS.server.learning.models.logits import AddNorm, BatchNormDense, QScoreNet


###############################################################################
class StrategyNet:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.perceptive_size = int(configuration.get("perceptive_field_size", 64))
        self.embedding_dims = int(configuration.get("embedding_dimensions", 200))
        self.neurons = int(configuration.get("qnet_neurons", 64))
        self.learning_rate = float(configuration.get("learning_rate", 0.0001))
        self.seed = int(configuration.get("training_seed", 42))
        self.q_neurons = self.neurons * 2
        self.action_size = STRATEGY_COUNT
        self.numbers = NUMBERS

        self.add_norm = AddNorm()
        self.timeseries = layers.Input(
            shape=(self.perceptive_size,), name="timeseries", dtype="int32"
        )
        self.gain_input = layers.Input(shape=(1,), name="gain", dtype="float32")
        self.embedding = RouletteEmbedding(
            self.embedding_dims, self.numbers, mask_padding=True
        )
        self.q_net = QScoreNet(self.q_neurons, self.action_size, self.seed)

    # -------------------------------------------------------------------------
    def compile_model(self, model: Model) -> Model:
        loss = losses.MeanSquaredError()
        metric = [metrics.RootMeanSquaredError()]
        optimizer = optimizers.AdamW(learning_rate=self.learning_rate)
        model.compile(loss=loss, optimizer=optimizer, metrics=metric, jit_compile=False)  # type: ignore
        return model

    # -------------------------------------------------------------------------
    def get_model(self, model_summary: bool = False) -> Model:
        embeddings = self.embedding(self.timeseries)
        layer = BatchNormDense(self.neurons)(embeddings)
        layer = BatchNormDense(self.neurons)(layer)
        layer = layers.Dropout(rate=0.3, seed=self.seed)(layer)
        layer = layers.Flatten()(layer)
        layer = BatchNormDense(self.neurons)(layer)

        context = BatchNormDense(max(1, self.neurons // 2))(self.gain_input)
        context = BatchNormDense(self.neurons)(context)

        merged = self.add_norm([layer, context])
        output = self.q_net(merged)

        model = Model(inputs=[self.timeseries, self.gain_input], outputs=output)
        model = self.compile_model(model)
        model.summary(expand_nested=True) if model_summary else None
        return model
