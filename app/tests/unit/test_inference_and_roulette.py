# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import pytest
import pandas as pd
import time
import os
import numpy as np
from server.learning.betting.hold import StrategyHold
from types import SimpleNamespace
from unittest.mock import Mock
from server.api.inference import start_session as start_session_api
from server.contracts.configuration import RouletteSettings, DatabaseSettings, JsonRouletteSettings
from server.contracts.inference import InferenceStartRequest, InferenceBetUpdateRequest, InferenceStepRequest
from server.services.inference import InferenceService
from sqlalchemy import create_engine, event, text
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import run_migrations_on_engine
from server.repositories.datasets import DatasetRepository
from server.repositories.inference import InferenceRepository
from typing import Any
from server.contracts.training import TrainingConfig
from pydantic import ValidationError
from server.common.constants import ROULETTE_COLOR_MAP
from server.common.roulette import build_roulette_number_pool, filter_roulette_series, validate_roulette_outcome
from server.learning.training.environment import RouletteWheelRenderer
from server.learning.betting.sizer import BetSizer
from server.learning.betting.types import STRATEGY_DALEMBERT, STRATEGY_FIBONACCI, STRATEGY_KEEP, STRATEGY_MARTINGALE, STRATEGY_REVERSE

###############################################################################
def test_hold_persists_strategy_for_configured_steps() -> None:
    selector = StrategyHold(hold_steps=3)

    assert selector.resolve(2) == 2
    assert selector.resolve(1) == 2
    assert selector.resolve(4) == 2
    assert selector.resolve(1) == 1

###############################################################################
def test_hold_requires_explicit_selection_when_uninitialized() -> None:
    selector = StrategyHold(hold_steps=2)

    with pytest.raises((TypeError, ValueError)):
        selector.resolve(None)  # type: ignore[arg-type]

###############################################################################
def test_hold_reset_clears_previous_strategy_state() -> None:
    selector = StrategyHold(hold_steps=3)
    assert selector.resolve(2) == 2
    assert selector.resolve(4) == 2

    selector.reset()
    assert selector.current_strategy_id is None
    assert selector.resolve(3) == 3
    assert selector.resolve(1) == 3
    assert selector.resolve(1) == 3
    assert selector.resolve(1) == 1

###############################################################################
def test_hold_steps_is_clamped_to_minimum_one() -> None:
    selector = StrategyHold(hold_steps=0)
    assert selector.resolve(4) == 4
    assert selector.resolve(2) == 2

###############################################################################
class RouletteSettingsFakePlayer:

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
class RouletteSettingsFakeDeviceConfig:

    # -------------------------------------------------------------------------
    def __init__(self, configuration):  # noqa: ANN001
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def set_device(self) -> None:
        return None

###############################################################################
def build_roulette_settings_service(monkeypatch, outcomes: list[int]) -> InferenceService:
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

    monkeypatch.setattr("server.services.inference.RoulettePlayer", RouletteSettingsFakePlayer)
    monkeypatch.setattr("server.services.inference.DeviceConfig", RouletteSettingsFakeDeviceConfig)

    return InferenceService(
        dataset_repository=dataset_repository,
        inference_repository=Mock(),
        checkpoint_service=checkpoint_service,
    )

###############################################################################
def test_session_start_filters_initial_context_to_runtime_pool(monkeypatch) -> None:
    service = build_roulette_settings_service(monkeypatch, [0, 4, 5, 6, 12])

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
    service = build_roulette_settings_service(monkeypatch, [0, 1, 2])

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

###############################################################################
class FakePlayer:

    # -------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
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
def test_capacity_bound_evicts_oldest_and_releases_models(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    event.listen(
        engine,
        "connect",
        lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
    )
    database = FAIRSDatabase(
        DatabaseSettings(True, None, None, None, None, None, None, False, None, 10, 1000),
        engine=engine,
    )
    run_migrations_on_engine(engine)
    dataset_repository = DatasetRepository(database)
    dataset = dataset_repository.import_replacement(
        "VAL22 capacity lineage",
        "inference",
        pd.DataFrame({"sequence_index": [0], "outcome_id": [17]}),
    )
    service, _ = build_service(monkeypatch)
    service.dataset_repository = dataset_repository
    service.inference_repository = InferenceRepository(database)
    created_players: list[FakePlayer] = []

    ###############################################################################
    class TrackingPlayer(FakePlayer):

        # -------------------------------------------------------------------------
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            super().__init__(*args, **kwargs)
            self.model = object()
            self.strategy_model = object()
            self.context = object()
            created_players.append(self)

    monkeypatch.setattr("server.services.inference.RoulettePlayer", TrackingPlayer)
    service.state.max_sessions = 16
    session_ids: list[str] = []
    cycle_durations: list[float] = []

    try:
        for _ in range(18):
            started_at = time.perf_counter()
            started = service.start_session(
                InferenceStartRequest(
                    checkpoint="cp1", dataset_id=dataset["dataset_id"]
                )
            )
            cycle_durations.append(time.perf_counter() - started_at)
            session_ids.append(started["session_id"])
            assert len(service.state.session_ids()) <= 16

        assert service.state.session_ids() == session_ids[-16:]
        with database.Session() as session:
            persisted = dict(
                session.execute(
                    text("SELECT session_id, ended_at FROM inference_sessions")
                ).all()
            )
        assert set(persisted) == set(session_ids)
        assert all(persisted[session_id] is not None for session_id in session_ids[:2])
        assert all(persisted[session_id] is None for session_id in session_ids[2:])

        for player in created_players[:2]:
            assert player.model is None
            assert player.strategy_model is None
            assert player.context is None

        service.shutdown()
        assert service.state.session_ids() == []
        with database.Session() as session:
            after_shutdown = dict(
                session.execute(
                    text("SELECT session_id, ended_at FROM inference_sessions")
                ).all()
            )
        assert all(after_shutdown[session_id] is not None for session_id in session_ids)
        for player in created_players:
            assert player.model is None
            assert player.strategy_model is None
            assert player.context is None
    finally:
        service.shutdown()
        database.dispose()

    print(
        "VAL22 inference capacity: "
        f"starts={len(cycle_durations)}, bound=16, total={sum(cycle_durations):.4f}s, "
        f"mean_per_start={sum(cycle_durations) / len(cycle_durations):.4f}s, "
        f"max={max(cycle_durations):.4f}s, timeout=none (unit service path), "
        f"evicted={session_ids[:2]}, persistence=ended"
    )

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

    ###############################################################################
    class TrackingPlayer(FakePlayer):

        # -------------------------------------------------------------------------
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
def test_replacement_start_failure_preserves_existing_session_and_releases_candidate(
    monkeypatch,
) -> None:
    service, _ = build_service(monkeypatch)
    service.state.max_sessions = 1
    existing = service.start_session(
        InferenceStartRequest(checkpoint="cp1", dataset_id=1)
    )
    existing_id = existing["session_id"]
    service.inference_repository.list_steps.return_value = []
    existing_snapshot = service.get_session_snapshot(existing_id)
    candidate_players: list[FakePlayer] = []

    ###############################################################################
    class TrackingPlayer(FakePlayer):

        # -------------------------------------------------------------------------
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            super().__init__(*args, **kwargs)
            self.model = object()
            candidate_players.append(self)

    monkeypatch.setattr("server.services.inference.RoulettePlayer", TrackingPlayer)
    service.inference_repository.create_session_with_initial_step.side_effect = (
        RuntimeError("replacement persistence failed")
    )

    with pytest.raises(RuntimeError, match="replacement persistence failed"):
        service.start_session(
            InferenceStartRequest(checkpoint="cp1", dataset_id=1),
            preserve_session_id=existing_id,
        )

    failed_candidate_id = service.inference_repository.delete_session.call_args.args[0]
    assert failed_candidate_id != existing_id
    assert service.state.session_ids() == [existing_id]
    assert service.state.get_session(existing_id).player is not None
    assert service.get_session_snapshot(existing_id) == existing_snapshot
    service.inference_repository.end_session.assert_not_called()
    service.inference_repository.delete_session.assert_called_once_with(
        failed_candidate_id
    )
    assert candidate_players[0].model is None

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
            "predicted_relative_preference": 0.9,
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
            "predicted_relative_preference": 0.9,
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

###############################################################################
class DummyModel:

    # -------------------------------------------------------------------------
    def predict(self, inputs: dict[str, Any], verbose: int = 0) -> np.ndarray:  # noqa: ARG002
        logits = np.zeros((1, 47), dtype=np.float32)
        logits[0, 12] = 1.0
        return logits

###############################################################################
class EmptyLogitsModel:

    # -------------------------------------------------------------------------
    def predict(self, inputs: dict[str, Any], verbose: int = 0) -> np.ndarray:  # noqa: ARG002
        return np.zeros((1, 0), dtype=np.float32)

###############################################################################
class StrategyLogitsModel:

    # -------------------------------------------------------------------------
    def __init__(self, strategy_id: int) -> None:
        self.strategy_id = strategy_id
        self.inputs: dict[str, np.ndarray] | None = None

    # -------------------------------------------------------------------------
    def predict(
        self, inputs: dict[str, np.ndarray], verbose: int = 0  # noqa: ARG002
    ) -> np.ndarray:
        self.inputs = inputs
        logits = np.zeros((1, 5), dtype=np.float32)
        logits[0, self.strategy_id] = 1.0
        return logits

###############################################################################
def build_configuration(**overrides: object) -> dict[str, object]:
    configuration = TrainingConfig(use_data_generator=True).model_dump()
    configuration.update(
        {
            "game_capital": configuration["initial_capital"],
            "game_bet": configuration["bet_amount"],
        }
    )
    configuration.update(overrides)
    return configuration

###############################################################################
def test_fixed_strategy_is_deterministic_when_strategy_model_disabled() -> None:
    os.environ.setdefault("KERAS_BACKEND", "torch")
    from server.learning.inference.player import RoulettePlayer

    config = build_configuration(
        seed=42,
        perceptive_field_size=4,
        game_capital=100,
        game_bet=10,
        dynamic_betting_enabled=True,
        bet_strategy_model_enabled=False,
        bet_strategy_fixed_id=3,
        strategy_hold_steps=2,
    )
    player = RoulettePlayer(
        model=DummyModel(),  # type: ignore[arg-type]
        configuration=config,
        session_id="session",
        dataset_context=pd.DataFrame({"outcome": [1, 2, 3, 4, 5, 6, 7, 8]}),
    )

    prediction = player.predict_next()

    assert prediction["bet_strategy_id"] == 3
    assert prediction["bet_strategy_name"] == "DAlembert"
    assert prediction["suggested_bet_amount"] == 10
    assert prediction["current_bet_amount"] == 10

###############################################################################
def test_strategy_model_selects_canonical_strategy_and_suggests_bet() -> None:
    os.environ.setdefault("KERAS_BACKEND", "torch")
    from server.learning.inference.player import RoulettePlayer

    config = build_configuration(
        seed=42,
        perceptive_field_size=4,
        game_capital=100,
        game_bet=10,
        dynamic_betting_enabled=True,
        bet_strategy_model_enabled=True,
        bet_strategy_fixed_id=0,
    )
    strategy_model = StrategyLogitsModel(strategy_id=3)
    player = RoulettePlayer(
        model=DummyModel(),  # type: ignore[arg-type]
        strategy_model=strategy_model,  # type: ignore[arg-type]
        configuration=config,
        session_id="strategy-session",
        dataset_context=pd.DataFrame({"outcome": [1, 2, 3, 4, 5, 6, 7, 8]}),
    )

    prediction = player.predict_next()

    assert prediction["bet_strategy_id"] == 3
    assert prediction["bet_strategy_name"] == "DAlembert"
    assert prediction["suggested_bet_amount"] == 10
    assert prediction["current_bet_amount"] == 10
    assert strategy_model.inputs is not None
    assert strategy_model.inputs["timeseries"].shape == (1, 4)
    assert strategy_model.inputs["gain"].shape == (1, 1)

###############################################################################
def test_predict_next_rejects_wrong_action_output_size() -> None:
    os.environ.setdefault("KERAS_BACKEND", "torch")
    from server.learning.inference.player import RoulettePlayer

    config = build_configuration(
        seed=42,
        perceptive_field_size=4,
        game_capital=100,
        game_bet=10,
        dynamic_betting_enabled=False,
    )
    player = RoulettePlayer(
        model=EmptyLogitsModel(),  # type: ignore[arg-type]
        configuration=config,
        session_id="session",
        dataset_context=pd.DataFrame({"outcome": [1, 2, 3, 4, 5, 6, 7, 8]}),
    )
    with pytest.raises(ValueError, match="canonical roulette action count"):
        player.predict_next()

###############################################################################
def test_predict_next_requires_minimum_context_length() -> None:
    os.environ.setdefault("KERAS_BACKEND", "torch")
    from server.learning.inference.player import RoulettePlayer

    config = build_configuration(
        seed=42,
        perceptive_field_size=8,
        game_capital=100,
        game_bet=10,
        dynamic_betting_enabled=False,
    )
    player = RoulettePlayer(
        model=DummyModel(),  # type: ignore[arg-type]
        configuration=config,
        session_id="session",
        dataset_context=pd.DataFrame({"outcome": [1, 2, 3]}),
    )
    with pytest.raises(ValueError, match="at least the perceptive field size"):
        player.predict_next()

###############################################################################
def test_update_with_true_extraction_validates_input() -> None:
    os.environ.setdefault("KERAS_BACKEND", "torch")
    from server.learning.inference.player import RoulettePlayer

    config = build_configuration(
        seed=42,
        perceptive_field_size=4,
        game_capital=100,
        game_bet=10,
        dynamic_betting_enabled=False,
    )
    player = RoulettePlayer(
        model=DummyModel(),  # type: ignore[arg-type]
        configuration=config,
        session_id="session",
        dataset_context=pd.DataFrame({"outcome": [1, 2, 3, 4, 5, 6, 7, 8]}),
    )
    player.predict_next()

    with pytest.raises(ValueError, match="must be an integer"):
        player.update_with_true_extraction("invalid")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="between 0 and 36"):
        player.update_with_true_extraction(37)

###############################################################################
def test_number_pool_applies_range_and_zero_exclusion() -> None:
    assert build_roulette_number_pool(5, 8) == (5, 6, 7, 8)
    assert build_roulette_number_pool(0, 3, exclude_zero=True) == (1, 2, 3)

###############################################################################
def test_invalid_or_empty_number_pool_is_rejected() -> None:
    with pytest.raises(ValueError, match="minimum"):
        build_roulette_number_pool(12, 4)
    with pytest.raises(ValueError, match="at least one"):
        build_roulette_number_pool(0, 0, exclude_zero=True)
    with pytest.raises(ValidationError, match="at least one"):
        JsonRouletteSettings(
            minimum_number=0,
            maximum_number=0,
            exclude_zero=True,
        )

###############################################################################
def test_series_filter_and_single_outcome_validation_use_same_pool() -> None:
    source = pd.DataFrame({"outcome": [0, 1, 2, 3, 4, 5]})

    filtered = filter_roulette_series(
        source,
        minimum_number=1,
        maximum_number=4,
        exclude_zero=True,
    )

    assert filtered["outcome"].tolist() == [1, 2, 3, 4]
    assert validate_roulette_outcome(
        4,
        minimum_number=1,
        maximum_number=4,
        exclude_zero=True,
    ) == 4
    with pytest.raises(ValueError, match="configured number pool"):
        validate_roulette_outcome(
            0,
            minimum_number=1,
            maximum_number=4,
            exclude_zero=True,
        )

###############################################################################
def test_renderer_inverts_visual_colors_without_changing_zero() -> None:
    red_numbers = ROULETTE_COLOR_MAP["red"]
    black_numbers = ROULETTE_COLOR_MAP["black"]
    normal = RouletteWheelRenderer(red_numbers, black_numbers)
    inverted = RouletteWheelRenderer(
        red_numbers,
        black_numbers,
        RouletteSettings(invert_colors=True, show_number_labels=False),
    )

    red_number = red_numbers[0]
    black_number = black_numbers[0]
    assert normal.get_number_color(red_number) == normal.base_red
    assert normal.get_number_color(black_number) == normal.base_black
    assert inverted.get_number_color(red_number) == inverted.base_black
    assert inverted.get_number_color(black_number) == inverted.base_red
    assert inverted.get_number_color(0) == inverted.base_green
    assert inverted.show_number_labels is False

###############################################################################
def build_sizer_configuration(**overrides: object) -> dict[str, object]:
    configuration = TrainingConfig(use_data_generator=True).model_dump()
    configuration.update(overrides)
    return configuration

###############################################################################
def test_keep_strategy_preserves_bet() -> None:
    sizer = BetSizer(build_sizer_configuration(bet_amount=10, initial_capital=1000))
    assert sizer.apply(STRATEGY_KEEP, capital=1000) == 10
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_KEEP, capital=1000) == 10

###############################################################################
def test_martingale_strategy_updates_deterministically() -> None:
    sizer = BetSizer(build_sizer_configuration(bet_amount=10, initial_capital=1000))
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 20
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 10

###############################################################################
def test_reverse_strategy_updates_deterministically() -> None:
    sizer = BetSizer(build_sizer_configuration(bet_amount=10, initial_capital=1000))
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_REVERSE, capital=1000) == 20
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_REVERSE, capital=1000) == 40
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_REVERSE, capital=1000) == 10

###############################################################################
def test_dalembert_strategy_updates_deterministically() -> None:
    sizer = BetSizer(
        build_sizer_configuration(bet_amount=10, bet_unit=5, initial_capital=1000)
    )
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_DALEMBERT, capital=1000) == 15
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_DALEMBERT, capital=1000) == 20
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_DALEMBERT, capital=1000) == 15
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_DALEMBERT, capital=1000) == 10

###############################################################################
def test_fibonacci_strategy_updates_deterministically() -> None:
    sizer = BetSizer(build_sizer_configuration(bet_amount=10, initial_capital=1000))
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 10
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 20
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 30
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 10

###############################################################################
def test_bounds_with_bet_max_and_capital_limit() -> None:
    sizer = BetSizer(
        build_sizer_configuration(
            bet_amount=10,
            initial_capital=1000,
            bet_max=25,
            bet_enforce_capital=True,
        )
    )
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 20
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 25
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=12) == 12

###############################################################################
def test_neutral_outcome_does_not_progress_sequences() -> None:
    sizer = BetSizer(build_sizer_configuration(bet_amount=10, initial_capital=1000))
    sizer.set_last_outcome_from_reward(0)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 10
    sizer.set_last_outcome_from_reward(0)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 10

###############################################################################
def test_none_bet_unit_falls_back_to_base_bet() -> None:
    sizer = BetSizer(
        build_sizer_configuration(bet_amount=10, bet_unit=None, initial_capital=1000)
    )
    assert sizer.unit == 10

###############################################################################
def test_preview_does_not_mutate_sizer_state() -> None:
    sizer = BetSizer(build_sizer_configuration(bet_amount=10, initial_capital=1000))
    sizer.set_last_outcome_from_reward(-10)
    before_bet = sizer.current_bet
    before_index = sizer.fib_index

    preview = sizer.preview(STRATEGY_MARTINGALE, capital=1000)

    assert preview == 20
    assert sizer.current_bet == before_bet
    assert sizer.fib_index == before_index

###############################################################################
def test_set_base_and_current_bet_respect_bounds() -> None:
    sizer = BetSizer(
        build_sizer_configuration(
            bet_amount=10,
            initial_capital=1000,
            bet_max=50,
            bet_enforce_capital=True,
        )
    )
    sizer.set_base_bet(40, capital=30)
    assert sizer.base_bet == 40
    assert sizer.current_bet == 30

    current = sizer.set_current_bet(100, capital=25)
    assert current == 25
    assert sizer.current_bet == 25
