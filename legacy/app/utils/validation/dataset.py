from __future__ import annotations

from typing import Any

import pandas as pd

from FAIRS.app.utils.validation.transitions import RouletteTransitionsVisualizer


# [VALIDATION OF DATA]
###############################################################################
class RouletteSeriesValidation:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.img_resolution = 400
        self.file_type = "jpeg"
        self.configuration = configuration
        self.transitions_visualizer = RouletteTransitionsVisualizer(configuration)

    # -------------------------------------------------------------------------
    def roulette_transitions(
        self,
        data: pd.DataFrame,
        metric_name: str = "roulette_transitions",
        **kwargs: Any,
    ) -> Any:
        return self.transitions_visualizer.generate_transition_plot(
            data, metric_name=metric_name, **kwargs
        )
