from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from server.api.inference import start_session as start_session_api
from server.contracts.configuration import RouletteSettings
from server.contracts.inference import InferenceStartRequest
from server.services.inference import InferenceService

###############################################################################
class FakePlayer:

    # -------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
        self.context = kwargs["dataset_context"]
        self.bet_amount = 10
        self.current_capital = 100
        self.action_descriptions = {index: f"action {index}" for index in range(47)}

    # -------------------------------------------------------------------------
    def predict_next(self) -> dict[str, object]:
        return {
            "action": 1,
            "description": "bet red",
            "relative_preference": 0.9,
        }

    # -------------------------------------------------------------------------
    def release(self) -> None:
        self.context = None

###############################################################################
class FakeDeviceConfig:

    # -------------------------------------------------------------------------
    def __init__(self, configuration):  # noqa: ANN001
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def set_device(self) -> None:
        return None

###############################################################################
def build_service(monkeypatch, outcomes: list[int]) -> InferenceService:
    dataset_repository = Mock()
    dataset_repository.get.return_value = {"dataset_id": 1}
    dataset_repository.outcomes.return_value = pd.DataFrame({"outcome": outcomes})

    checkpoint_service = Mock()
    checkpoint_service.resolve_existing_checkpoint.return_value = ("cp1", "path/cp1")
    checkpoint_service.load_checkpoint.return_value = (
        object(),
        {
            "dynamic_betting_enabled": False,
            "bet_strategy_model_enabled": False,
        },
        {},
        "path/cp1",
    )

    monkeypatch.setattr("server.services.inference.RoulettePlayer", FakePlayer)
    monkeypatch.setattr("server.services.inference.DeviceConfig", FakeDeviceConfig)

    return InferenceService(
        dataset_repository=dataset_repository,
        inference_repository=Mock(),
        checkpoint_service=checkpoint_service,
    )

###############################################################################
def test_session_start_filters_initial_context_to_runtime_pool(monkeypatch) -> None:
    service = build_service(monkeypatch, [0, 4, 5, 6, 12])

    result = service.start_session(
        InferenceStartRequest(checkpoint="cp1", dataset_id=1),
        roulette_settings=RouletteSettings(
            minimum_number=5,
            maximum_number=10,
            exclude_zero=True,
        ),
    )

    session = service.state.get_session(result["session_id"])
    assert session.player is not None
    assert session.player.context["outcome"].tolist() == [5, 6]

###############################################################################
def test_session_start_rejects_context_emptied_by_runtime_pool(monkeypatch) -> None:
    service = build_service(monkeypatch, [0, 1, 2])

    with pytest.raises(ValueError, match="No inference outcomes remain"):
        service.start_session(
            InferenceStartRequest(checkpoint="cp1", dataset_id=1),
            roulette_settings=RouletteSettings(
                minimum_number=5,
                maximum_number=10,
                exclude_zero=True,
            ),
        )

    service.inference_repository.create_session_with_initial_step.assert_not_called()

###############################################################################
def test_api_passes_current_roulette_settings_to_session_start() -> None:
    service = Mock()
    service.start_session.return_value = {
        "session_id": "session-1",
        "checkpoint": "cp1",
        "game_capital": 100,
        "game_bet": 1,
        "current_capital": 100,
        "prediction": {
            "action": 1,
            "description": "bet red",
            "relative_preference": 0.9,
        },
    }
    settings_service = Mock()
    settings_service.get_settings.return_value = SimpleNamespace(
        roulette=SimpleNamespace(
            minimum_number=5,
            maximum_number=10,
            exclude_zero=True,
            invert_colors=True,
            show_number_labels=False,
        )
    )
    payload = InferenceStartRequest(checkpoint="cp1", dataset_id=1)

    response = start_session_api(payload, service, settings_service)

    assert response.session_id == "session-1"
    _, kwargs = service.start_session.call_args
    assert kwargs["roulette_settings"] == RouletteSettings(
        minimum_number=5,
        maximum_number=10,
        exclude_zero=True,
        invert_colors=True,
        show_number_labels=False,
    )
