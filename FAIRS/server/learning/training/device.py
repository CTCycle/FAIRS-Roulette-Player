from __future__ import annotations

from typing import Any

import torch
from keras.mixed_precision import set_global_policy

from FAIRS.server.common.utils.logger import logger


###############################################################################
class DeviceConfig:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def set_device(self) -> torch.device:
        use_gpu = self.configuration.get("use_device_gpu", False)
        device_name = "cuda" if use_gpu else "cpu"
        mixed_precision = self.configuration.get("use_mixed_precision", False)

        device = torch.device("cpu")
        cuda_available = torch.cuda.is_available()

        if device_name == "cuda":
            if cuda_available:
                device_id = self.configuration.get("device_id", 0)
                device = torch.device(f"cuda:{device_id}")
                torch.cuda.set_device(device_id)
                logger.info(f"GPU (cuda:{device_id}) is set as the active device.")
                if mixed_precision:
                    set_global_policy("mixed_float16")
                    logger.info("Mixed precision policy is active during training")
            else:
                logger.info("No GPU found (torch.cuda.is_available() is False). Falling back to CPU.")
                logger.info("CPU is set as the active device.")
        else:
            logger.info("CPU is set as the active device.")

        return device