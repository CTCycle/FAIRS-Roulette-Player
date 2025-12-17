from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from FAIRS.app.client.workers import check_thread_status, update_progress_callback
from FAIRS.app.utils.logger import logger


###############################################################################
class RouletteTransitionsVisualizer:
    def __init__(self, configuration: dict[str, object]) -> None:
        self.configuration = configuration
        self.figsize = (18, 8)
        self.file_type = "jpeg"
        self.dpi = 300
        self.stream_name = "roulette_transitions"

    # -------------------------------------------------------------------------
    def generate_transition_plot(
        self,
        data: pd.DataFrame,
        metric_name: str = "roulette_transitions",
        progress_callback=None,
        worker=None,
    ) -> plt.Figure:
        check_thread_status(worker)
        dataframe = self._prepare_dataframe(data)
        check_thread_status(worker)

        color_matrix, color_states = self._compute_transition_matrix(
            dataframe["color"].astype(str)
        )
        position_transitions = self._compute_position_transitions(dataframe["position"])
        figure = self._create_figure(color_matrix, color_states, position_transitions)

        payload = self._figure_to_payload(figure, metric_name)
        if progress_callback:
            progress_callback(payload)
            update_progress_callback(1, 1, progress_callback)

        return figure

    # -------------------------------------------------------------------------
    def _prepare_dataframe(self, data: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(data, pd.DataFrame):
            dataframe = pd.DataFrame(data)
        else:
            dataframe = data.copy()

        required_columns = {"extraction", "color", "position"}
        missing = required_columns.difference(dataframe.columns)
        if missing:
            message = f"Roulette dataset is missing required columns: {sorted(missing)}"
            logger.error(message)
            raise ValueError(message)

        dataframe = dataframe.sort_values("extraction").reset_index(drop=True)
        dataframe = dataframe.dropna(subset=["color", "position"])
        if dataframe.empty:
            message = "Roulette dataset is empty after removing invalid rows"
            logger.error(message)
            raise ValueError(message)

        return dataframe

    # -------------------------------------------------------------------------
    def _compute_transition_matrix(
        self, series: pd.Series
    ) -> tuple[np.ndarray, list[str]]:
        states = list(dict.fromkeys(series.dropna().tolist()))
        size = len(states)
        if size <= 1:
            return np.zeros((0, 0), dtype=int), []

        matrix = np.zeros((size, size), dtype=int)
        index_lookup = {state: idx for idx, state in enumerate(states)}
        previous = None
        for current in series:
            if previous is not None:
                i = index_lookup[previous]
                j = index_lookup[current]
                matrix[i, j] += 1
            previous = current

        return matrix, states

    # -------------------------------------------------------------------------
    def _compute_position_transitions(self, series: pd.Series) -> pd.DataFrame:
        previous = series.shift(1)
        dataframe = pd.DataFrame({"from": previous, "to": series})
        dataframe = dataframe.dropna()
        if dataframe.empty:
            return pd.DataFrame(columns=["from", "to", "count"])

        grouped = (
            dataframe.groupby(["from", "to"], dropna=True)
            .size()
            .reset_index(name="count")
        )
        grouped["from"] = grouped["from"].astype(int)
        grouped["to"] = grouped["to"].astype(int)
        grouped = grouped.sort_values("count", ascending=False)

        return grouped

    # -------------------------------------------------------------------------
    def _create_figure(
        self,
        matrix: np.ndarray,
        states: list[str],
        position_transitions: pd.DataFrame,
    ) -> plt.Figure:
        figure, axes = plt.subplots(1, 2, figsize=self.figsize)

        self._plot_color_transitions(axes[0], matrix, states)
        self._plot_position_transitions(axes[1], position_transitions)
        figure.suptitle("Roulette Transition Analysis", fontsize=16)
        figure.tight_layout(rect=(0, 0, 1, 0.95))

        return figure

    # -------------------------------------------------------------------------
    def _plot_color_transitions(
        self, axis: plt.Axes, matrix: np.ndarray, states: list[str]
    ) -> None:
        axis.set_title("Color-to-Color Transition Probability")
        if matrix.size == 0 or not states:
            axis.text(0.5, 0.5, "Not enough data", ha="center", va="center")
            axis.axis("off")
            return

        totals = matrix.sum(axis=1, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            probabilities = np.divide(matrix, totals, where=totals != 0)
        im = axis.imshow(probabilities, cmap="viridis", vmin=0, vmax=1)
        axis.set_xticks(range(len(states)))
        axis.set_yticks(range(len(states)))
        axis.set_xticklabels(states, rotation=45, ha="right")
        axis.set_yticklabels(states)
        for i in range(len(states)):
            for j in range(len(states)):
                if totals[i, 0] == 0:
                    continue
                probability = probabilities[i, j]
                count = matrix[i, j]
                axis.text(
                    j,
                    i,
                    f"{probability:.2f}\n({count})",
                    ha="center",
                    va="center",
                    color="white" if probability > 0.5 else "black",
                    fontsize=10,
                )
        axis.set_xlabel("Next Color")
        axis.set_ylabel("Current Color")
        figure = axis.get_figure()
        figure.colorbar(im, ax=axis, fraction=0.046, pad=0.04, label="Probability")

    # -------------------------------------------------------------------------
    def _plot_position_transitions(
        self, axis: plt.Axes, transitions: pd.DataFrame
    ) -> None:
        axis.set_title("Top Position Transitions")
        if transitions.empty:
            axis.text(0.5, 0.5, "Not enough data", ha="center", va="center")
            axis.axis("off")
            return

        top_transitions = transitions.head(10)
        renamed = top_transitions.rename(columns={"from": "from_"})
        labels = [f"{int(row.from_)} → {int(row.to)}" for row in renamed.itertuples()]
        counts = top_transitions["count"].to_numpy()
        positions = np.arange(len(labels))
        axis.barh(positions, counts, color="#1f77b4")
        axis.set_yticks(positions)
        axis.set_yticklabels(labels)
        axis.invert_yaxis()
        axis.set_xlabel("Occurrences")
        for idx, value in enumerate(counts):
            axis.text(value + 0.1, positions[idx], str(int(value)), va="center")

    # -------------------------------------------------------------------------
    def _figure_to_payload(self, figure: plt.Figure, metric_name: str) -> dict:
        buffer = BytesIO()
        figure.savefig(
            buffer,
            format=self.file_type,
            dpi=self.dpi,
            bbox_inches="tight",
        )
        data = buffer.getvalue()
        buffer.close()

        payload = {
            "kind": "render",
            "source": "train_metrics",
            "stream": metric_name or self.stream_name,
            "data": data,
        }

        return payload
