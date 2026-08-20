from __future__ import annotations

from unittest.mock import Mock

import pytest

from server.contracts.inference import (
    InferenceBetUpdateRequest,
    InferenceStartRequest,
    InferenceStepRequest,
)
from server.services.inference import InferenceService

###############################################################################
class FakePlayer:

    # -------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
        self.bet_amount = 10
        self.current_capital = 100

    # -------------------------------------------------------------------------
    def predict_next(self) -> dict[str, object]:
        return {"action": 1, "description": "bet red", "confidence": 0.9}

    # -------------------------------------------------------------------------
    def update_with_true_extraction(self, extraction: int) -> tuple[int, int]:
        return (1, 101 if extraction >= 0 else 100)

    # -------------------------------------------------------------------------
    def update_bet_amount(self, bet_amount: int) -> None:
        self.bet_amount = bet_amount

###############################################################################
class FakeDeviceConfig:

    # -------------------------------------------------------------------------
    def __init__(self, configuration):  # noqa: ANN001
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def set_device(self) -> None:
        return None

###############################################################################
def build_service(monkeypatch) -> tuple[InferenceService, Mock]:
    data_store = Mock()
    data_store.load_dataset.return_value = {"dataset_id": 1}

    checkpoint_service = Mock()
    checkpoint_service.resolve_existing_checkpoint.return_value = ("cp1", "path/cp1")
    checkpoint_service.load_checkpoint.return_value = (
        object(),
        {"dynamic_betting_enabled": False},
        {},
        "path/cp1",
    )
    checkpoint_service.load_strategy_model.return_value = None

    monkeypatch.setattr("server.services.inference.RoulettePlayer", FakePlayer)
    monkeypatch.setattr("server.services.inference.DeviceConfig", FakeDeviceConfig)

    service = InferenceService(
        data_store=data_store, checkpoint_service=checkpoint_service
    )
    return service, data_store

###############################################################################
def test_session_lifecycle_and_prediction_flow(monkeypatch) -> None:
    service, data_store = build_service(monkeypatch)
    start = service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))
    session_id = start["session_id"]
    assert start["checkpoint"] == "cp1"
    data_store.load_dataset_outcomes.assert_called_once_with(1)

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
    data_store.mark_inference_session_ended.assert_called_once_with(session_id)

###############################################################################
def test_clear_rows_preserves_session_header(monkeypatch) -> None:
    service, data_store = build_service(monkeypatch)
    response = service.clear_session_rows("session_1")
    assert response == {"session_id": "session_1", "status": "cleared"}
    data_store.clear_inference_session_steps.assert_called_once_with("session_1")
    data_store.delete_inference_session.assert_not_called()

###############################################################################
def test_capacity_eviction_closes_persisted_session(monkeypatch) -> None:
    service, data_store = build_service(monkeypatch)
    service.state.max_sessions = 1

    first = service.start_session(
        InferenceStartRequest(checkpoint="cp1", dataset_id=1)
    )
    second = service.start_session(
        InferenceStartRequest(checkpoint="cp1", dataset_id=1)
    )

    first_id = first["session_id"]
    second_id = second["session_id"]
    assert first_id not in service.state.sessions
    assert second_id in service.state.sessions
    data_store.mark_inference_session_ended.assert_called_once_with(first_id)

###############################################################################
def test_replacing_session_closes_previous_persisted_session(monkeypatch) -> None:
    service, data_store = build_service(monkeypatch)
    first = service.start_session(
        InferenceStartRequest(checkpoint="cp1", dataset_id=1)
    )

    second = service.start_session(
        InferenceStartRequest(
            checkpoint="cp1",
            dataset_id=1,
            session_id=first["session_id"],
        )
    )

    assert first["session_id"] not in service.state.sessions
    assert second["session_id"] in service.state.sessions
    data_store.mark_inference_session_ended.assert_called_once_with(first["session_id"])

###############################################################################
def test_clear_context_rejects_active_session(monkeypatch) -> None:
    service, data_store = build_service(monkeypatch)
    service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))

    with pytest.raises(RuntimeError, match="active"):
        service.clear_context()

    data_store.clear_datasets.assert_not_called()

###############################################################################
def test_clear_context_succeeds_after_session_shutdown(monkeypatch) -> None:
    service, data_store = build_service(monkeypatch)
    start = service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))
    service.shutdown_session(start["session_id"])

    assert service.clear_context() == {"status": "cleared"}
    data_store.clear_datasets.assert_called_once_with("inference")
