from __future__ import annotations

from typing import Any

from keras import Model, layers, losses, metrics, optimizers
from torch import compile as torch_compile

from FAIRS.app.utils.constants import NUMBERS, STATES
from FAIRS.app.utils.learning.models.embeddings import RouletteEmbedding
from FAIRS.app.utils.learning.models.logits import AddNorm, BatchNormDense, QScoreNet


# [FAIRS MODEL]
###############################################################################
class FAIRSnet:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.perceptive_size = configuration.get("perceptive_field_size", 64)
        self.embedding_dims = configuration.get("embedding_dimensions", 200)
        self.neurons = configuration.get("QNet_neurons", 64)
        self.jit_compile = configuration.get("jit_compile", False)
        self.jit_backend = configuration.get("jit_backend", "inductor")
        self.learning_rate = configuration.get("learning_rate", 0.0001)
        self.seed = configuration.get("training_seed", 42)
        self.q_neurons = self.neurons * 2
        self.action_size = STATES
        self.numbers = NUMBERS
        self.add_norm = AddNorm()
        self.timeseries = layers.Input(
            shape=(self.perceptive_size,), name="timeseries", dtype="int32"
        )
        # second input: gain metric (current capital over initial capital)
        self.gain_input = layers.Input(shape=(1,), name="gain", dtype="float32")
        self.embedding = RouletteEmbedding(
            self.embedding_dims, self.numbers, mask_padding=True
        )
        # initialize QNet for Q scores predictions
        self.QNet = QScoreNet(self.q_neurons, self.action_size, self.seed)

    # -------------------------------------------------------------------------
    def compile_model(self, model: Model, model_summary: bool = True) -> Model | Any:
        # define model compilation parameters such as learning rate, loss, metrics and optimizer
        loss = losses.MeanSquaredError()
        metric = [metrics.RootMeanSquaredError()]
        opt = optimizers.AdamW(learning_rate=self.learning_rate)
        model.compile(loss=loss, optimizer=opt, metrics=metric, jit_compile=False)  # type: ignore
        # print model summary on console and run torch.compile
        # with triton compiler and selected backend
        model.summary(expand_nested=True) if model_summary else None
        if self.jit_compile:
            model = torch_compile(model, backend=self.jit_backend, mode="default")  # type: ignore

        return model

    # build model given the architecture
    # -------------------------------------------------------------------------
    def get_model(self, model_summary: bool = True) -> Model:
        embeddings = self.embedding(self.timeseries)
        layer = BatchNormDense(self.neurons)(embeddings)
        layer = BatchNormDense(self.neurons)(layer)
        layer = layers.Dropout(rate=0.3, seed=self.seed)(layer)

        # process gain context with a couple of dense layers and match dimensions
        ctx = BatchNormDense(self.neurons // 2)(self.gain_input)
        ctx = BatchNormDense(self.neurons)(ctx)

        # add + normalize to inject context into the main stream
        merged = self.add_norm([layer, ctx])

        output = self.QNet(merged)

        # define the model from inputs and outputs
        model = Model(inputs=[self.timeseries, self.gain_input], outputs=output)
        model = self.compile_model(model, model_summary=model_summary)

        return model
