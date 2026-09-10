from __future__ import annotations

from typing import Any

import torch
from keras.mixed_precision import set_global_policy

from server.common.utils.logger import logger

###############################################################################
class DeviceConfig:

    # -------------------------------------------------------------------------
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def set_device(self) -> torch.device:
        use_gpu = bool(self.configuration["use_device_gpu"])
        mixed_precision = bool(self.configuration["use_mixed_precision"])
        set_global_policy("mixed_float16" if mixed_precision else "float32")

        if use_gpu:
            if not torch.cuda.is_available():
                raise RuntimeError(
                    "GPU training was requested, but CUDA is unavailable."
                )
            device_id = self.configuration["device_id"]
            if (
                isinstance(device_id, bool)
                or not isinstance(device_id, int)
                or device_id < 0
                or device_id >= torch.cuda.device_count()
            ):
                raise RuntimeError(f"CUDA device_id is invalid: {device_id!r}")
            device = torch.device(f"cuda:{device_id}")
            torch.cuda.set_device(device_id)
            logger.info("GPU (cuda:%s) is set as the active device.", device_id)
            if mixed_precision:
                logger.info("Mixed precision policy is active during training")
            return device

        logger.info("CPU is set as the active device.")
        return torch.device("cpu")
