from __future__ import annotations

import time
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from server.contracts.inference import (
    InferenceBetUpdateRequest,
    InferenceStartRequest,
    InferenceStepRequest,
)
from server.learning.inference.player import RoulettePlayer
from server.learning.training.device import DeviceConfig
from server.repositories.datasets import DatasetRepository
from server.repositories.inference import InferenceRepository
from server.services.checkpoints import CheckpointService
from server.common.utils.logger import logger


###############################################################################
class InferenceSession:
    # -------------------------------------------------------------------------
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
        self.player: RoulettePlayer | None = player
        self.lock = threading.RLock()
        self.initial_capital = int(initial_capital)
        self.current_bet = int(current_bet)
        self.started_at = datetime.now(timezone.utc)
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
        if self.player is None:
            raise RuntimeError("Inference session is closed.")
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
        if self.player is None:
            raise RuntimeError("Inference session is closed.")
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
        if self.player is None:
            raise RuntimeError("Inference session is closed.")
        self.current_bet = int(bet_amount)
        self.player.update_bet_amount(bet_amount)

    # -------------------------------------------------------------------------
    def release(self) -> None:
        """Drop model, strategy, and dataset references owned by this session."""
        player = self.player
        if player is None:
            return
        for attribute in ("model", "strategy_model", "context"):
            if hasattr(player, attribute):
                setattr(player, attribute, None)
        self.last_prediction = None
        self.player = None


###############################################################################
class InferenceState:
    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        self.sessions: dict[str, InferenceSession] = {}
        self.max_sessions = 16
        self.lock = threading.RLock()

    # -------------------------------------------------------------------------
    def create_session(self, session: InferenceSession) -> list[InferenceSession]:
        with self.lock:
            self.sessions[session.session_id] = session
            return self._cleanup_locked()

    # -------------------------------------------------------------------------
    def add_session(self, session: InferenceSession) -> None:
        with self.lock:
            self.sessions[session.session_id] = session

    # -------------------------------------------------------------------------
    def sessions_to_evict(
        self,
        additional_sessions: int = 1,
        excluded_session_ids: set[str] | None = None,
    ) -> list[InferenceSession]:
        with self.lock:
            required = len(self.sessions) + additional_sessions - self.max_sessions
            if required <= 0:
                return []
            ordered = sorted(
                (
                    session
                    for session in self.sessions.values()
                    if excluded_session_ids is None
                    or session.session_id not in excluded_session_ids
                ),
                key=lambda item: item.last_seen,
            )
            return ordered[:required]

    # -------------------------------------------------------------------------
    def get_session(self, session_id: str) -> InferenceSession:
        with self.lock:
            session = self.sessions.get(session_id)
        if session is None:
            raise KeyError("Session not found.")
        return session

    # -------------------------------------------------------------------------
    def get_optional(self, session_id: str) -> InferenceSession | None:
        with self.lock:
            return self.sessions.get(session_id)

    # -------------------------------------------------------------------------
    def delete_session(self, session_id: str) -> InferenceSession | None:
        with self.lock:
            return self.sessions.pop(session_id, None)

    # -------------------------------------------------------------------------
    def session_ids(self) -> list[str]:
        with self.lock:
            return list(self.sessions)

    # -------------------------------------------------------------------------
    def has_sessions(self) -> bool:
        with self.lock:
            return bool(self.sessions)

    # -------------------------------------------------------------------------
    def cleanup(self) -> list[InferenceSession]:
        with self.lock:
            return self._cleanup_locked()

    # -------------------------------------------------------------------------
    def _cleanup_locked(self) -> list[InferenceSession]:
        if len(self.sessions) <= self.max_sessions:
            return []
        ordered = sorted(self.sessions.values(), key=lambda item: item.last_seen)
        return ordered[: max(0, len(ordered) - self.max_sessions)]


###############################################################################
class InferenceService:
    # -------------------------------------------------------------------------
    def __init__(
        self,
        dataset_repository: DatasetRepository,
        inference_repository: InferenceRepository,
        checkpoint_service: CheckpointService,
    ) -> None:
        self.dataset_repository = dataset_repository
        self.inference_repository = inference_repository
        self.checkpoint_service = checkpoint_service
        self.state = InferenceState()
        self._operation_lock = threading.RLock()
        self._shutting_down = False
        self._shutdown_complete = False

    # -------------------------------------------------------------------------
    def _ensure_active(self) -> None:
        if self._shutting_down:
            raise RuntimeError("Inference service is shutting down.")

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
        self.inference_repository.upsert_session(row)

    # -------------------------------------------------------------------------
    def _build_session_header(self, session: InferenceSession) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "dataset_id": session.dataset_id,
            "checkpoint_name": session.checkpoint,
            "initial_capital": session.initial_capital,
            "started_at": session.started_at,
            "ended_at": None,
        }

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
            "recorded_at": datetime.now(timezone.utc),
        }
        self.inference_repository.upsert_step(row)

    # -------------------------------------------------------------------------
    def _build_session_step(
        self,
        session: InferenceSession,
        prediction: dict[str, Any],
        step_number: int,
        observed_outcome: int | None,
        reward: int | None,
        capital_after: int | None,
    ) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "step_number": step_number,
            "bet_amount": session.current_bet,
            "predicted_action": int(prediction.get("action", 0)),
            "predicted_confidence": prediction.get("confidence"),
            "observed_outcome_id": observed_outcome,
            "reward": reward,
            "capital_after": capital_after,
            "recorded_at": datetime.now(timezone.utc),
        }

    # -------------------------------------------------------------------------
    def _close_session(
        self,
        session_id: str,
        *,
        mark_missing: bool = False,
        session: InferenceSession | None = None,
        force: bool = False,
    ) -> None:
        active_session = session or self.state.get_optional(session_id)
        if active_session is None:
            if mark_missing:
                self.inference_repository.end_session(session_id)
            return

        closed = False
        try:
            with active_session.lock:
                self.inference_repository.end_session(session_id)
            closed = True
        except Exception:
            if not force:
                raise
            logger.exception("Failed to persist shutdown for inference session %s", session_id)
        if closed or force:
            self.state.delete_session(session_id)
            active_session.release()

    # -------------------------------------------------------------------------
    def _discard_session_after_failure(
        self, session_id: str, session: InferenceSession
    ) -> None:
        try:
            self.inference_repository.end_session(session_id)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to persist failed inference session shutdown %s", session_id
            )
        self.state.delete_session(session_id)
        session.release()

    # -------------------------------------------------------------------------
    def _evict_sessions(self, sessions: list[InferenceSession]) -> None:
        """Persist and release a capacity eviction as one logical operation."""
        persisted: list[InferenceSession] = []
        try:
            for session in sessions:
                with session.lock:
                    self.inference_repository.end_session(session.session_id)
                persisted.append(session)
        except Exception:
            for session in reversed(persisted):
                restore = getattr(self.inference_repository, "restore_session", None)
                if not callable(restore):
                    logger.error(
                        "Cannot roll back inference eviction for session %s; "
                        "repository has no restore operation",
                        session.session_id,
                    )
                    continue
                try:
                    restore(session.session_id)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Failed to roll back inference eviction for session %s",
                        session.session_id,
                    )
            raise

        for session in persisted:
            self.state.delete_session(session.session_id)
            session.release()

    # -------------------------------------------------------------------------
    def start_session(
        self,
        payload: InferenceStartRequest,
        *,
        preserve_session_id: str | None = None,
    ) -> dict[str, Any]:
        with self._operation_lock:
            self._ensure_active()
            model: Any | None = None
            strategy_model = None
            player: RoulettePlayer | None = None
            session: InferenceSession | None = None
            session_id = uuid.uuid4().hex
            try:
                checkpoint, checkpoint_path = (
                    self.checkpoint_service.resolve_existing_checkpoint(
                        payload.checkpoint
                    )
                )

                dataset_id = payload.dataset_id
                dataset = self.dataset_repository.get(dataset_id)
                if dataset is None:
                    raise FileNotFoundError(f"Dataset '{dataset_id}' was not found.")
                dataset_context = self.dataset_repository.outcomes(dataset_id)

                model, train_config, _, _ = self.checkpoint_service.load_checkpoint(
                    checkpoint
                )
                configuration = {
                    **train_config,
                    "game_capital": payload.game_capital,
                    "game_bet": payload.game_bet,
                }

                device = DeviceConfig(configuration)
                device.set_device()

                if bool(configuration.get("dynamic_betting_enabled", False)) and bool(
                    configuration.get("bet_strategy_model_enabled", False)
                ):
                    strategy_model = self.checkpoint_service.load_strategy_model(
                        checkpoint_path, required=True
                    )
                player = RoulettePlayer(
                    model=model,
                    configuration=configuration,
                    session_id=session_id,
                    dataset_context=dataset_context,
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
                self.inference_repository.create_session_with_initial_step(
                    self._build_session_header(session),
                    self._build_session_step(
                        session,
                        prediction,
                        1,
                        None,
                        None,
                        int(player.current_capital),
                    ),
                )
                excluded_session_ids = (
                    {preserve_session_id}
                    if preserve_session_id is not None
                    and self.state.get_optional(preserve_session_id) is not None
                    else None
                )
                self._evict_sessions(
                    self.state.sessions_to_evict(
                        excluded_session_ids=excluded_session_ids,
                    )
                )
                self.state.add_session(session)
            except Exception:
                if session is not None:
                    try:
                        self.inference_repository.delete_session(session_id)
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "Failed to roll back inference session %s", session_id
                        )
                if session is not None:
                    session.release()
                elif player is not None:
                    for attribute in ("model", "strategy_model", "context"):
                        if hasattr(player, attribute):
                            setattr(player, attribute, None)
                    player = None
                model = None
                strategy_model = None
                raise

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
        with self._operation_lock:
            self._ensure_active()
            session = self.state.get_session(session_id)
            with session.lock:
                if session.prediction_pending:
                    raise RuntimeError("Prediction already pending for this session.")
                prediction = session.predict()
                try:
                    self.persist_session_step(
                        session,
                        prediction,
                        session.prediction_step,
                        None,
                        None,
                        int(session.player.current_capital) if session.player else None,
                    )
                except Exception:
                    self._discard_session_after_failure(session_id, session)
                    raise
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
        with self._operation_lock:
            self._ensure_active()
            session = self.state.get_session(session_id)
            with session.lock:
                step_payload, last_prediction = session.step(payload.extraction)
                try:
                    self.persist_session_step(
                        session,
                        last_prediction or {},
                        int(step_payload["step"]),
                        int(step_payload["real_extraction"]),
                        int(step_payload["reward"]),
                        int(step_payload["capital_after"]),
                    )
                except Exception:
                    self._discard_session_after_failure(session_id, session)
                    raise
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
    def update_bet(
        self, session_id: str, payload: InferenceBetUpdateRequest
    ) -> dict[str, Any]:
        with self._operation_lock:
            self._ensure_active()
            session = self.state.get_session(session_id)
            with session.lock:
                session.update_bet(payload.bet_amount)
                if session.prediction_pending and session.last_prediction is not None:
                    try:
                        self.persist_session_step(
                            session,
                            session.last_prediction,
                            session.prediction_step,
                            None,
                            None,
                            int(session.player.current_capital)
                            if session.player
                            else None,
                        )
                    except Exception:
                        self._discard_session_after_failure(session_id, session)
                        raise
                return {"session_id": session_id, "bet_amount": session.current_bet}

    # -------------------------------------------------------------------------
    def shutdown_session(self, session_id: str) -> dict[str, Any]:
        with self._operation_lock:
            self._ensure_active()
            self._close_session(session_id, mark_missing=True)
            return {"session_id": session_id, "status": "closed"}

    # -------------------------------------------------------------------------
    def clear_session_rows(self, session_id: str) -> dict[str, Any]:
        with self._operation_lock:
            self._ensure_active()
            if self.state.get_optional(session_id) is not None:
                raise RuntimeError("Cannot clear rows for an active session.")
            self.inference_repository.clear_steps(session_id)
            return {"session_id": session_id, "status": "cleared"}

    # -------------------------------------------------------------------------
    def clear_context(self) -> dict[str, str]:
        with self._operation_lock:
            self._ensure_active()
            if self.state.has_sessions():
                raise RuntimeError(
                    "Cannot clear inference context while an inference session is active."
                )
            self.dataset_repository.clear("inference")
            return {"status": "cleared"}

    # -------------------------------------------------------------------------
    def get_session_snapshot(self, session_id: str) -> dict[str, Any]:
        with self._operation_lock:
            self._ensure_active()
            session = self.state.get_session(session_id)
            with session.lock:
                player = session.player
                if player is None:
                    raise KeyError("Session not found.")
                descriptions = getattr(player, "action_descriptions", {})
                steps = []
                for row in self.inference_repository.list_steps(session_id):
                    action = int(row["predicted_action"])
                    steps.append(
                        {
                            "step": int(row["step_number"]),
                            "bet_amount": int(row["bet_amount"]),
                            "predicted_action": action,
                            "predicted_action_desc": str(
                                descriptions.get(action, f"action {action}")
                            ),
                            "predicted_confidence": row.get("predicted_confidence"),
                            "observed_outcome_id": row.get("observed_outcome_id"),
                            "reward": row.get("reward"),
                            "capital_after": int(row["capital_after"]),
                        }
                    )
                return {
                    "session_id": session.session_id,
                    "checkpoint": session.checkpoint,
                    "dataset_id": session.dataset_id,
                    "initial_capital": session.initial_capital,
                    "current_capital": int(player.current_capital),
                    "current_bet": session.current_bet,
                    "step_count": session.step_count,
                    "prediction_pending": session.prediction_pending,
                    "last_prediction": dict(session.last_prediction)
                    if session.last_prediction is not None
                    else None,
                    "steps": steps,
                }

    # -------------------------------------------------------------------------
    def shutdown(self) -> None:
        with self._operation_lock:
            if self._shutdown_complete:
                return
            self._shutting_down = True
            for session_id in self.state.session_ids():
                session = self.state.get_optional(session_id)
                try:
                    self._close_session(
                        session_id,
                        session=session,
                        force=True,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Unexpected inference session shutdown failure %s", session_id
                    )
            self._shutdown_complete = True
