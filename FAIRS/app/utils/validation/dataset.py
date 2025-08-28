# [VALIDATION OF DATA]
###############################################################################
from typing import Any, Dict


class RouletteSeriesValidation:
    def __init__(self, configuration: Dict[str, Any]) -> None:
        self.img_resolution = 400
        self.file_type = "jpeg"
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def placeholder_method(self, data, **kwargs) -> None:
        pass
