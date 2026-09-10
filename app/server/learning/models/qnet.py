from __future__ import annotations

from typing import Any

from keras import Model, layers, losses, metrics, optimizers
from torch import compile as torch_compile

from server.common.constants import NUMBERS, STATES
from server.learning.models.embeddings import RouletteEmbedding
from server.learning.models.logits import AddNorm, BatchNormDense, QScoreNet

###############################################################################
class FAIRSnet:

    # -------------------------------------------------------------------------
    def __init__(
        self,
        configuration: dict[str, Any],
        *,
        jit_compile: bool = False,
        jit_backend: str = "inductor",
    ) -> None:
        self.perceptive_size = configuration["perceptive_field_size"]
        self.embedding_dims = configuration["embedding_dimensions"]
        self.neurons = configuration["qnet_neurons"]
        self.jit_compile = bool(jit_compile)
        self.jit_backend = jit_backend
        self.learning_rate = configuration["learning_rate"]
        self.seed = configuration["training_seed"]
        self.q_neurons = self.neurons * 2
        self.action_size = STATES
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
    def compile_model(self, model: Model, model_summary: bool = True) -> Model | Any:
        loss = losses.MeanSquaredError()
        metric = [metrics.RootMeanSquaredError()]
        opt = optimizers.AdamW(learning_rate=self.learning_rate)
        model.compile(loss=loss, optimizer=opt, metrics=metric, jit_compile=False)  # type: ignore
        model.summary(expand_nested=True) if model_summary else None
        if self.jit_compile:
            model = torch_compile(model, backend=self.jit_backend, mode="default")

        return model

    # -------------------------------------------------------------------------
    def get_model(self, model_summary: bool = True) -> Model:
        embeddings = self.embedding(self.timeseries)
        layer = BatchNormDense(self.neurons)(embeddings)
        layer = BatchNormDense(self.neurons)(layer)
        layer = layers.Dropout(rate=0.3, seed=self.seed)(layer)
        layer = layers.Flatten()(layer)
        layer = BatchNormDense(self.neurons)(layer)

        ctx = BatchNormDense(self.neurons // 2)(self.gain_input)
        ctx = BatchNormDense(self.neurons)(ctx)

        merged = self.add_norm([layer, ctx])
        output = self.q_net(merged)

        model = Model(inputs=[self.timeseries, self.gain_input], outputs=output)
        model = self.compile_model(model, model_summary=model_summary)

        return model
