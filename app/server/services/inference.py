from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from server.domain.inference import (
    InferenceBetUpdateRequest,
    InferenceStartRequest,
    InferenceStepRequest,
)
from server.learning.inference.player import RoulettePlayer
from server.learning.training.device import DeviceConfig
from server.repositories.serialization.data import DataSerializer
from server.services.checkpoints import CheckpointService


###############################################################################
class InferenceSession:
    def __init__(
        self,
        session_id: str,
        checkpoint: str,
        dataset_id: int,
        player: RoulettePlayer,
        initial_capital: int,
        current_bet: int,
    ) -> None:
        self.session_id = session_id
        self.checkpoint = checkpoint
        self.dataset_id = dataset_id
        self.player = player
        self.initial_capital = int(initial_capital)
        self.current_bet = int(current_bet)
        self.started_at = datetime.now()
        self.step_count = 0
        self.last_seen = time.time()
        self.last_prediction: dict[str, Any] | None = None
        self.prediction_pending = False
        self.prediction_step = 0

    # -------------------------------------------------------------------------
    def touch(self) -> None:
        self.last_seen = time.time()

    # -------------------------------------------------------------------------
    def predict(self) -> dict[str, Any]:
        self.touch()
        prediction = self.player.predict_next()
        if "current_bet_amount" in prediction:
            self.current_bet = int(prediction["current_bet_amount"])
        self.last_prediction = prediction
        self.prediction_pending = True
        self.prediction_step = self.step_count + 1
        return prediction

    # -------------------------------------------------------------------------
    def step(self, extraction: int) -> tuple[dict[str, Any], dict[str, Any]]:
        self.touch()
        if self.last_prediction is None or not self.prediction_pending:
            raise ValueError("No prediction available for this step.")

        predicted_action = int(self.last_prediction["action"])
        predicted_action_desc = str(self.last_prediction["description"])
        reward, capital_after = self.player.update_with_true_extraction(extraction)

        self.step_count += 1
        step_payload = {
            "step": int(self.step_count),
            "real_extraction": int(extraction),
            "predicted_action": predicted_action,
            "predicted_action_desc": predicted_action_desc,
            "reward": int(reward),
            "capital_after": int(capital_after),
        }
        self.prediction_pending = False
        return step_payload, self.last_prediction

    # -------------------------------------------------------------------------
    def update_bet(self, bet_amount: int) -> None:
        self.current_bet = int(bet_amount)
        self.player.update_bet_amount(bet_amount)


###############################################################################
class InferenceState:
    def __init__(self) -> None:
        self.sessions: dict[str, InferenceSession] = {}
        self.max_sessions = 16

    # -------------------------------------------------------------------------
    def create_session(self, session: InferenceSession) -> None:
        self.sessions[session.session_id] = session
        self.cleanup()

    # -------------------------------------------------------------------------
    def get_session(self, session_id: str) -> InferenceSession:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError("Session not found.")
        return session

    # -------------------------------------------------------------------------
    def delete_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]

    # -------------------------------------------------------------------------
    def cleanup(self) -> None:
        if len(self.sessions) <= self.max_sessions:
            return
        ordered = sorted(self.sessions.values(), key=lambda item: item.last_seen)
        for stale in ordered[: max(0, len(ordered) - self.max_sessions)]:
            del self.sessions[stale.session_id]


###############################################################################
class InferenceService:
    def __init__(
        self,
        serializer: DataSerializer,
        checkpoint_service: CheckpointService,
    ) -> None:
        self.serializer = serializer
        self.checkpoint_service = checkpoint_service
        self.model_serializer = checkpoint_service.model_serializer
        self.state = InferenceState()

    # -------------------------------------------------------------------------
    def persist_session_header(self, session: InferenceSession) -> None:
        row = {
            "session_id": session.session_id,
            "dataset_id": session.dataset_id,
            "checkpoint_name": session.checkpoint,
            "initial_capital": session.initial_capital,
            "started_at": session.started_at,
            "ended_at": None,
        }
        self.serializer.upsert_inference_session(row)

    # -------------------------------------------------------------------------
    def persist_session_step(
        self,
        session: InferenceSession,
        prediction: dict[str, Any],
        step_number: int,
        observed_outcome: int | None,
        reward: int | None,
        capital_after: int | None,
    ) -> None:
        row = {
            "session_id": session.session_id,
            "step_number": step_number,
            "bet_amount": session.current_bet,
            "predicted_action": int(prediction.get("action", 0)),
            "predicted_confidence": prediction.get("confidence"),
            "observed_outcome_id": observed_outcome,
            "reward": reward,
            "capital_after": capital_after,
            "recorded_at": datetime.now(),
        }
        self.serializer.upsert_inference_session_step(row)

    # -------------------------------------------------------------------------
    def start_session(self, payload: InferenceStartRequest) -> dict[str, Any]:
        checkpoint, checkpoint_path = self.checkpoint_service.resolve_existing_checkpoint(
            payload.checkpoint
        )

        dataset_id = int(payload.dataset_id)
        session_id = uuid.uuid4().hex
        if payload.session_id:
            self.state.delete_session(payload.session_id)

        dataset = self.serializer.load_dataset(dataset_id)
        if dataset is None:
            raise FileNotFoundError(f"Dataset '{dataset_id}' was not found.")

        model, train_config, _, _ = self.model_serializer.load_checkpoint(checkpoint)
        configuration = {
            **train_config,
            "game_capital": payload.game_capital,
            "game_bet": payload.game_bet,
            "dynamic_betting_enabled": bool(
                payload.dynamic_betting_enabled
                or train_config.get("dynamic_betting_enabled", False)
            ),
            "bet_strategy_model_enabled": bool(
                payload.bet_strategy_model_enabled
                or train_config.get("bet_strategy_model_enabled", False)
            ),
            "bet_strategy_fixed_id": int(
                train_config.get("bet_strategy_fixed_id", payload.bet_strategy_fixed_id)
            ),
            "strategy_hold_steps": int(
                train_config.get("strategy_hold_steps", payload.strategy_hold_steps)
            ),
            "bet_unit": payload.bet_unit
            if payload.bet_unit is not None
            else train_config.get("bet_unit"),
            "bet_max": payload.bet_max
            if payload.bet_max is not None
            else train_config.get("bet_max"),
            "bet_enforce_capital": bool(
                train_config.get("bet_enforce_capital", payload.bet_enforce_capital)
            ),
            "auto_apply_bet_suggestions": payload.auto_apply_bet_suggestions,
        }

        device = DeviceConfig(configuration)
        device.set_device()

        strategy_model = None
        if bool(configuration.get("dynamic_betting_enabled", False)) and bool(
            configuration.get("bet_strategy_model_enabled", False)
        ):
            strategy_model = self.model_serializer.load_strategy_model(
                checkpoint_path, required=True
            )
        player = RoulettePlayer(
            model=model,
            configuration=configuration,
            session_id=session_id,
            dataset_id=dataset_id,
            serializer=self.serializer,
            dataset_source=payload.dataset_source,
            strategy_model=strategy_model,
        )
        prediction = player.predict_next()

        session = InferenceSession(
            session_id,
            checkpoint,
            dataset_id,
            player,
            int(payload.game_capital),
            int(player.bet_amount),
        )
        session.last_prediction = prediction
        session.prediction_pending = True
        session.prediction_step = 1
        self.state.create_session(session)
        self.persist_session_header(session)
        self.persist_session_step(
            session,
            prediction,
            1,
            None,
            None,
            int(player.current_capital),
        )

        return {
            "session_id": session_id,
            "checkpoint": checkpoint,
            "game_capital": int(payload.game_capital),
            "game_bet": int(player.bet_amount),
            "current_capital": int(player.current_capital),
            "prediction": prediction,
        }

    # -------------------------------------------------------------------------
    def next_prediction(self, session_id: str) -> dict[str, Any]:
        session = self.state.get_session(session_id)
        if session.prediction_pending:
            raise RuntimeError("Prediction already pending for this session.")
        prediction = session.predict()
        self.persist_session_step(
            session,
            prediction,
            session.prediction_step,
            None,
            None,
            int(session.player.current_capital),
        )
        return {
            "session_id": session_id,
            "prediction": prediction,
        }

    # -------------------------------------------------------------------------
    def step_session(
        self,
        session_id: str,
        payload: InferenceStepRequest,
    ) -> dict[str, Any]:
        session = self.state.get_session(session_id)
        step_payload, last_prediction = session.step(payload.extraction)
        self.persist_session_step(
            session,
            last_prediction or {},
            int(step_payload["step"]),
            int(step_payload["real_extraction"]),
            int(step_payload["reward"]),
            int(step_payload["capital_after"]),
        )
        return {
            "session_id": session_id,
            "step": step_payload["step"],
            "real_extraction": step_payload["real_extraction"],
            "predicted_action": step_payload["predicted_action"],
            "predicted_action_desc": step_payload["predicted_action_desc"],
            "reward": step_payload["reward"],
            "capital_after": step_payload["capital_after"],
        }

    # -------------------------------------------------------------------------
    def update_bet(self, session_id: str, payload: InferenceBetUpdateRequest) -> dict[str, Any]:
        session = self.state.get_session(session_id)
        session.update_bet(payload.bet_amount)
        if session.prediction_pending and session.last_prediction is not None:
            self.persist_session_step(
                session,
                session.last_prediction,
                session.prediction_step,
                None,
                None,
                int(session.player.current_capital),
            )
        return {"session_id": session_id, "bet_amount": session.current_bet}

    # -------------------------------------------------------------------------
    def shutdown_session(self, session_id: str) -> dict[str, Any]:
        self.serializer.mark_inference_session_ended(session_id)
        self.state.delete_session(session_id)
        return {"session_id": session_id, "status": "closed"}

    # -------------------------------------------------------------------------
    def clear_session_rows(self, session_id: str) -> dict[str, Any]:
        self.serializer.clear_inference_session_steps(session_id)
        return {"session_id": session_id, "status": "cleared"}

    # -------------------------------------------------------------------------
    def clear_context(self) -> dict[str, str]:
        self.serializer.clear_datasets("inference")
        return {"status": "cleared"}
