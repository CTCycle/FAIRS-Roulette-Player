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
    dataset_repository = Mock()
    dataset_repository.get.return_value = {"dataset_id": 1}
    dataset_repository.outcomes.return_value = []
    inference_repository = Mock()

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
        dataset_repository=dataset_repository,
        inference_repository=inference_repository,
        checkpoint_service=checkpoint_service,
    )
    return service, dataset_repository


###############################################################################
def test_session_lifecycle_and_prediction_flow(monkeypatch) -> None:
    service, dataset_repository = build_service(monkeypatch)
    start = service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))
    session_id = start["session_id"]
    assert start["checkpoint"] == "cp1"
    dataset_repository.outcomes.assert_called_once_with(1)

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
    service.inference_repository.end_session.assert_called_once_with(session_id)


###############################################################################
def test_clear_rows_preserves_session_header(monkeypatch) -> None:
    service, _ = build_service(monkeypatch)
    response = service.clear_session_rows("session_1")
    assert response == {"session_id": "session_1", "status": "cleared"}
    service.inference_repository.clear_steps.assert_called_once_with("session_1")
    service.inference_repository.delete_session.assert_not_called()


###############################################################################
def test_capacity_eviction_closes_persisted_session(monkeypatch) -> None:
    service, _ = build_service(monkeypatch)
    service.state.max_sessions = 1

    first = service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))
    second = service.start_session(
        InferenceStartRequest(checkpoint="cp1", dataset_id=1)
    )

    first_id = first["session_id"]
    second_id = second["session_id"]
    assert first_id not in service.state.sessions
    assert second_id in service.state.sessions
    service.inference_repository.end_session.assert_called_once_with(first_id)


###############################################################################
def test_clear_context_rejects_active_session(monkeypatch) -> None:
    service, dataset_repository = build_service(monkeypatch)
    service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))

    with pytest.raises(RuntimeError, match="active"):
        service.clear_context()

    dataset_repository.clear.assert_not_called()


###############################################################################
def test_clear_context_succeeds_after_session_shutdown(monkeypatch) -> None:
    service, dataset_repository = build_service(monkeypatch)
    start = service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))
    service.shutdown_session(start["session_id"])

    assert service.clear_context() == {"status": "cleared"}
    dataset_repository.clear.assert_called_once_with("inference")


###############################################################################
def test_shutdown_session_keeps_live_state_when_persistence_close_fails(monkeypatch) -> None:
    service, _ = build_service(monkeypatch)
    start = service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))
    service.inference_repository.end_session.side_effect = RuntimeError(
        "close persistence failed"
    )

    with pytest.raises(RuntimeError, match="close persistence failed"):
        service.shutdown_session(start["session_id"])

    assert service.state.get_optional(start["session_id"]) is not None
    assert service.state.get_session(start["session_id"]).player is not None


###############################################################################
def test_session_start_rolls_back_persistence_and_model_on_registration_failure(
    monkeypatch,
) -> None:
    service, _ = build_service(monkeypatch)
    released_players: list[FakePlayer] = []

    class TrackingPlayer(FakePlayer):
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            super().__init__(*args, **kwargs)
            self.model = object()
            released_players.append(self)

    monkeypatch.setattr("server.services.inference.RoulettePlayer", TrackingPlayer)
    service.inference_repository.create_session_with_initial_step.side_effect = RuntimeError(
        "persistence failed"
    )

    with pytest.raises(RuntimeError, match="persistence failed"):
        service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))

    service.inference_repository.delete_session.assert_called_once()
    assert not service.state.has_sessions()
    assert released_players[0].model is None


###############################################################################
def test_session_snapshot_returns_authoritative_persisted_steps(monkeypatch) -> None:
    service, _ = build_service(monkeypatch)
    start = service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))
    session_id = start["session_id"]
    service.inference_repository.list_steps.return_value = [
        {
            "step_number": 1,
            "bet_amount": 10,
            "predicted_action": 1,
            "predicted_confidence": 0.9,
            "observed_outcome_id": 12,
            "reward": 1,
            "capital_after": 101,
        }
    ]

    snapshot = service.get_session_snapshot(session_id)

    assert snapshot["session_id"] == session_id
    assert snapshot["current_capital"] == 100
    assert snapshot["step_count"] == 0
    assert snapshot["steps"] == [
        {
            "step": 1,
            "bet_amount": 10,
            "predicted_action": 1,
            "predicted_action_desc": "action 1",
            "predicted_confidence": 0.9,
            "observed_outcome_id": 12,
            "reward": 1,
            "capital_after": 101,
        }
    ]


###############################################################################
def test_capacity_eviction_failure_keeps_existing_session_live(monkeypatch) -> None:
    service, _ = build_service(monkeypatch)
    service.state.max_sessions = 1
    first = service.start_session(
        InferenceStartRequest(checkpoint="cp1", dataset_id=1)
    )
    service.inference_repository.end_session.side_effect = RuntimeError(
        "eviction persistence failed"
    )

    with pytest.raises(RuntimeError, match="eviction persistence failed"):
        service.start_session(InferenceStartRequest(checkpoint="cp1", dataset_id=1))

    assert service.state.get_optional(first["session_id"]) is not None
    assert len(service.state.session_ids()) == 1
    service.inference_repository.delete_session.assert_called()


###############################################################################
def test_shutdown_is_failure_isolated_and_idempotent(monkeypatch) -> None:
    service, _ = build_service(monkeypatch)
    service.state.max_sessions = 2
    first = service.start_session(
        InferenceStartRequest(checkpoint="cp1", dataset_id=1)
    )
    second = service.start_session(
        InferenceStartRequest(checkpoint="cp1", dataset_id=1)
    )
    service.inference_repository.end_session.side_effect = [RuntimeError("first"), None]

    service.shutdown()
    service.shutdown()

    assert not service.state.has_sessions()
    assert service.inference_repository.end_session.call_count == 2
    assert first["session_id"] != second["session_id"]
