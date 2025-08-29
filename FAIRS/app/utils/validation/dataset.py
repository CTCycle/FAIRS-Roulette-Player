from __future__ import annotations

from typing import Any, Dict


# [VALIDATION OF DATA]
###############################################################################
class RouletteSeriesValidation:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.img_resolution = 400
        self.file_type = "jpeg"
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def placeholder_method(self, data, **kwargs) -> None:
        pass
