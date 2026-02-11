from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from FAIRS.server.entities.inference import (
    InferenceBetUpdateRequest,
    InferenceNextResponse,
    InferenceShutdownResponse,
    InferenceStartRequest,
    InferenceStartResponse,
    InferenceStepRequest,
    InferenceStepResponse,
    PredictionResponse,
)
from FAIRS.server.common.utils.logger import logger
from FAIRS.server.learning.inference.player import RoulettePlayer
from FAIRS.server.learning.training.device import DeviceConfig
from FAIRS.server.repositories.serialization.data import DataSerializer
from FAIRS.server.repositories.serialization.model import ModelSerializer


router = APIRouter(prefix="/inference", tags=["inference"])


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

    # -----------------------------------------------------------------------------
    def touch(self) -> None:
        self.last_seen = time.time()

    # -----------------------------------------------------------------------------
    def predict(self) -> dict[str, Any]:
        self.touch()
        prediction = self.player.predict_next()
        self.last_prediction = prediction
        self.prediction_pending = True
        self.prediction_step = self.step_count + 1
        return prediction

    # -----------------------------------------------------------------------------
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

    # -----------------------------------------------------------------------------
    def update_bet(self, bet_amount: int) -> None:
        self.current_bet = int(bet_amount)
        self.player.update_bet_amount(bet_amount)


###############################################################################
class InferenceState:
    def __init__(self) -> None:
        self.sessions: dict[str, InferenceSession] = {}
        self.max_sessions = 16

    # -----------------------------------------------------------------------------
    def create_session(self, session: InferenceSession) -> None:
        self.sessions[session.session_id] = session
        self.cleanup()

    # -----------------------------------------------------------------------------
    def get_session(self, session_id: str) -> InferenceSession:
        session = self.sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        return session

    # -----------------------------------------------------------------------------
    def delete_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]

    # -----------------------------------------------------------------------------
    def cleanup(self) -> None:
        if len(self.sessions) <= self.max_sessions:
            return
        ordered = sorted(self.sessions.values(), key=lambda item: item.last_seen)
        for stale in ordered[: max(0, len(ordered) - self.max_sessions)]:
            del self.sessions[stale.session_id]


inference_state = InferenceState()


###############################################################################
class InferenceEndpoint:
    def __init__(self, router: APIRouter) -> None:
        self.router = router
        self.model_serializer = ModelSerializer()
        self.serializer = DataSerializer()

    # -------------------------------------------------------------------------
    def persist_session_header(
        self,
        session: InferenceSession,
    ) -> None:
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

    # -----------------------------------------------------------------------------
    def start_session(self, payload: InferenceStartRequest) -> InferenceStartResponse:
        checkpoint_raw = payload.checkpoint
        checkpoint = checkpoint_raw.strip()
        dataset_id = int(payload.dataset_id)
        session_id = uuid.uuid4().hex
        if payload.session_id:
            inference_state.delete_session(payload.session_id)

        if not checkpoint:
            logger.warning("Rejected inference start: empty checkpoint from payload.checkpoint")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Checkpoint identifier is required.",
            )
        if checkpoint != checkpoint_raw:
            logger.info(
                "Normalized checkpoint from payload.checkpoint: '%s' -> '%s'",
                checkpoint_raw,
                checkpoint,
            )

        available_checkpoints = self.model_serializer.scan_checkpoints_folder()
        if checkpoint not in available_checkpoints:
            logger.warning(
                "Rejected inference start: unknown checkpoint from payload.checkpoint (%s). Available=%d",
                checkpoint,
                len(available_checkpoints),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint '{checkpoint}' was not found.",
            )

        dataset = self.serializer.load_dataset(dataset_id)
        if dataset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset '{dataset_id}' was not found.",
            )

        logger.info(
            "Resolved inference checkpoint from payload.checkpoint: %s (dataset=%s, session_id=%s)",
            checkpoint,
            dataset_id,
            session_id,
        )

        try:
            logger.info("Loading %s checkpoint for inference", checkpoint)
            model, train_config, _, _ = self.model_serializer.load_checkpoint(checkpoint)
        except Exception as exc:
            logger.exception("Failed to load checkpoint %s", checkpoint)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checkpoint not found or invalid.",
            ) from exc

        configuration = {**train_config, "game_capital": payload.game_capital, "game_bet": payload.game_bet}

        try:
            device = DeviceConfig(configuration)
            device.set_device()
        except Exception as exc:
            logger.exception("Failed to set inference device configuration")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to initialize inference device.",
            ) from exc

        try:
            player = RoulettePlayer(
                model,
                configuration,
                session_id,
                dataset_id,
                payload.dataset_source,
            )
            prediction = player.predict_next()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("Failed to initialize inference session")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to start inference session.",
            ) from exc

        session = InferenceSession(
            session_id,
            checkpoint,
            dataset_id,
            player,
            int(payload.game_capital),
            int(payload.game_bet),
        )
        session.last_prediction = prediction
        session.prediction_pending = True
        session.prediction_step = 1
        inference_state.create_session(session)
        self.persist_session_header(session)

        self.persist_session_step(
            session,
            prediction,
            1,
            None,
            None,
            int(player.current_capital),
        )

        return InferenceStartResponse(
            session_id=session_id,
            checkpoint=checkpoint,
            game_capital=int(payload.game_capital),
            game_bet=int(payload.game_bet),
            current_capital=int(player.current_capital),
            prediction=PredictionResponse(**prediction),
        )

    # -----------------------------------------------------------------------------
    def next_prediction(self, session_id: str) -> InferenceNextResponse:
        session = inference_state.get_session(session_id)
        if session.prediction_pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prediction already pending for this session.",
            )
        try:
            prediction = session.predict()
        except Exception as exc:
            logger.exception("Failed to compute next prediction")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to compute next prediction.",
            ) from exc

        self.persist_session_step(
            session,
            prediction,
            session.prediction_step,
            None,
            None,
            int(session.player.current_capital),
        )

        return InferenceNextResponse(
            session_id=session_id,
            prediction=PredictionResponse(**prediction),
        )

    # -----------------------------------------------------------------------------
    def submit_step(self, session_id: str, payload: InferenceStepRequest) -> InferenceStepResponse:
        session = inference_state.get_session(session_id)
        try:
            step_payload, last_prediction = session.step(payload.extraction)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("Failed to execute inference step")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to execute inference step.",
            ) from exc

        self.persist_session_step(
            session,
            last_prediction or {},
            int(step_payload["step"]),
            int(step_payload["real_extraction"]),
            int(step_payload["reward"]),
            int(step_payload["capital_after"]),
        )

        return InferenceStepResponse(
            session_id=session_id,
            step=step_payload["step"],
            real_extraction=step_payload["real_extraction"],
            predicted_action=step_payload["predicted_action"],
            predicted_action_desc=step_payload["predicted_action_desc"],
            reward=step_payload["reward"],
            capital_after=step_payload["capital_after"],
        )

    # -----------------------------------------------------------------------------
    def shutdown(self, session_id: str) -> InferenceShutdownResponse:
        self.serializer.mark_inference_session_ended(session_id)
        inference_state.delete_session(session_id)
        return InferenceShutdownResponse(session_id=session_id, status="closed")

    # -------------------------------------------------------------------------
    def update_bet_amount(
        self, session_id: str, payload: InferenceBetUpdateRequest
    ) -> dict[str, Any]:
        session = inference_state.get_session(session_id)
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
    def clear_session_rows(self, session_id: str) -> dict[str, Any]:
        self.serializer.delete_inference_session(session_id)
        return {"session_id": session_id, "status": "cleared"}

    # -------------------------------------------------------------------------
    def clear_inference_context(self) -> dict[str, str]:
        self.serializer.clear_datasets("inference")
        return {"status": "cleared"}

    # -----------------------------------------------------------------------------
    def add_routes(self) -> None:
        self.router.add_api_route(
            "/sessions/start",
            self.start_session,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/sessions/{session_id}/next",
            self.next_prediction,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/sessions/{session_id}/step",
            self.submit_step,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/sessions/{session_id}/shutdown",
            self.shutdown,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/sessions/{session_id}/bet",
            self.update_bet_amount,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/sessions/{session_id}/rows/clear",
            self.clear_session_rows,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/context/clear",
            self.clear_inference_context,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )


inference_endpoint = InferenceEndpoint(router=router)
inference_endpoint.add_routes()

