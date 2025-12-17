from __future__ import annotations

from typing import Any

import pandas as pd
import tensorflow as tf


# wrapper function to run the data pipeline from raw inputs to tensor dataset
###############################################################################
class RouletteDataLoader:
    def __init__(self, configuration: dict[str, Any], shuffle: bool = True) -> None:
        pass
        # self.processor = DataLoaderProcessor(configuration)
        # self.batch_size = configuration.get('batch_size', 32)
        # self.inference_batch_size = configuration.get('inference_batch_size', 32)
        # self.shuffle_samples = configuration.get('shuffle_size', 1024)
        # self.buffer_size = tf.data.AUTOTUNE
        # self.configuration = configuration
        # self.shuffle = shuffle

    # effectively build the tf.dataset and apply preprocessing, batching and prefetching
    # -------------------------------------------------------------------------
    def build_training_dataloader(
        self, data: pd.DataFrame, batch_size: int | None = None
    ) -> pd.DataFrame:
        # images, tokens = data['path'].to_list(), data['tokens'].to_list()
        # batch_size = self.batch_size if batch_size is None else batch_size
        # dataset = tf.data.Dataset.from_tensor_slices((images, tokens))
        # dataset = dataset.map(
        #     self.processor.load_data_for_training, num_parallel_calls=self.buffer_size)
        # dataset = dataset.batch(batch_size)
        # dataset = dataset.prefetch(buffer_size=self.buffer_size)
        # dataset = dataset.shuffle(buffer_size=self.shuffle_samples) if self.shuffle else dataset

        return data

    # effectively build the tf.dataset and apply preprocessing, batching and prefetching
    # -------------------------------------------------------------------------
    def build_inference_dataloader(
        self, data, batch_size: int | None = None, buffer_size: int = tf.data.AUTOTUNE
    ) -> Any:
        # images, tokens = data['path'].to_list(), data['tokens'].to_list()
        # batch_size = self.inference_batch_size if batch_size is None else batch_size
        # dataset = tf.data.Dataset.from_tensor_slices((images, tokens))
        # dataset = dataset.map(
        #     self.processor.load_data_for_inference, num_parallel_calls=buffer_size)
        # dataset = dataset.batch(batch_size)
        # dataset = dataset.prefetch(buffer_size=buffer_size)

        return data
