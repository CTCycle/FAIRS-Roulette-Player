from __future__ import annotations

from unittest.mock import Mock

import pytest

from FAIRS.server.domain.inference import (
    InferenceBetUpdateRequest,
    InferenceStartRequest,
    InferenceStepRequest,
)
from FAIRS.server.services.inference import InferenceService


class FakePlayer:
    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
        self.bet_amount = 10
        self.current_capital = 100

    def predict_next(self) -> dict[str, object]:
        return {"action": 1, "description": "bet red", "confidence": 0.9}

    def update_with_true_extraction(self, extraction: int) -> tuple[int, int]:
        return (1, 101 if extraction >= 0 else 100)

    def update_bet_amount(self, bet_amount: int) -> None:
        self.bet_amount = bet_amount


class FakeDeviceConfig:
    def __init__(self, configuration):  # noqa: ANN001
        self.configuration = configuration

    def set_device(self) -> None:
        return None


def build_service(monkeypatch) -> tuple[InferenceService, Mock]:
    serializer = Mock()
    serializer.load_dataset.return_value = {"dataset_id": 1}

    checkpoint_service = Mock()
    checkpoint_service.resolve_existing_checkpoint.return_value = ("cp1", "path/cp1")
    checkpoint_service.model_serializer.load_checkpoint.return_value = (
        object(),
        {"dynamic_betting_enabled": False},
        {},
        "path/cp1",
    )
    checkpoint_service.model_serializer.load_strategy_model.return_value = None

    monkeypatch.setattr("FAIRS.server.services.inference.RoulettePlayer", FakePlayer)
    monkeypatch.setattr("FAIRS.server.services.inference.DeviceConfig", FakeDeviceConfig)

    service = InferenceService(serializer=serializer, checkpoint_service=checkpoint_service)
    return service, serializer


def test_session_lifecycle_and_prediction_flow(monkeypatch) -> None:
    service, serializer = build_service(monkeypatch)
    start = service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))
    session_id = start["session_id"]
    assert start["checkpoint"] == "cp1"

    with pytest.raises(RuntimeError):
        service.next_prediction(session_id)

    step = service.step_session(session_id, InferenceStepRequest(extraction=10))
    assert step["session_id"] == session_id

    next_payload = service.next_prediction(session_id)
    assert next_payload["session_id"] == session_id

    bet = service.update_bet(session_id, InferenceBetUpdateRequest(bet_amount=25))
    assert bet["bet_amount"] == 25

    shutdown = service.shutdown_session(session_id)
    assert shutdown["status"] == "closed"
    serializer.mark_inference_session_ended.assert_called_once_with(session_id)


def test_clear_rows_preserves_session_header(monkeypatch) -> None:
    service, serializer = build_service(monkeypatch)
    response = service.clear_session_rows("session_1")
    assert response == {"session_id": "session_1", "status": "cleared"}
    serializer.clear_inference_session_steps.assert_called_once_with("session_1")
    serializer.delete_inference_session.assert_not_called()
