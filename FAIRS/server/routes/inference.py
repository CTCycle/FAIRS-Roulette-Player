from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, status

from FAIRS.server.schemas.inference import (
    InferenceNextResponse,
    InferenceShutdownResponse,
    InferenceStartRequest,
    InferenceStartResponse,
    InferenceStepRequest,
    InferenceStepResponse,
    PredictionResponse,
)
from FAIRS.server.utils.logger import logger
from FAIRS.server.utils.services.inference.player import RoulettePlayer
from FAIRS.server.utils.services.training.device import DeviceConfig
from FAIRS.server.utils.services.training.serializer import ModelSerializer


router = APIRouter(prefix="/inference", tags=["inference"])


###############################################################################
class InferenceSession:
    def __init__(
        self,
        session_id: str,
        checkpoint: str,
        dataset_name: str,
        player: RoulettePlayer,
    ) -> None:
        self.session_id = session_id
        self.checkpoint = checkpoint
        self.dataset_name = dataset_name
        self.player = player
        self.step_count = 0
        self.last_seen = time.time()
        self.last_prediction: dict[str, Any] | None = None

    # -----------------------------------------------------------------------------
    def touch(self) -> None:
        self.last_seen = time.time()

    # -----------------------------------------------------------------------------
    def predict(self) -> dict[str, Any]:
        self.touch()
        prediction = self.player.predict_next()
        self.last_prediction = prediction
        return prediction

    # -----------------------------------------------------------------------------
    def step(self, extraction: int) -> tuple[dict[str, Any], dict[str, Any]]:
        self.touch()
        if self.last_prediction is None:
            self.last_prediction = self.player.predict_next()

        predicted_action = int(self.last_prediction["action"])
        predicted_action_desc = str(self.last_prediction["description"])
        reward, capital_after = self.player.update_with_true_extraction(extraction)
        self.player.save_prediction(self.checkpoint)

        self.step_count += 1
        next_prediction = self.player.predict_next()
        self.last_prediction = next_prediction  # Update for next step
        step_payload = {
            "step": int(self.step_count),
            "real_extraction": int(extraction),
            "predicted_action": predicted_action,
            "predicted_action_desc": predicted_action_desc,
            "reward": int(reward),
            "capital_after": int(capital_after),
        }
        return step_payload, next_prediction


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

    # -----------------------------------------------------------------------------
    def start_session(self, payload: InferenceStartRequest) -> InferenceStartResponse:
        checkpoint = payload.checkpoint
        dataset_name = payload.dataset_name
        session_id = uuid.uuid4().hex

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
            player = RoulettePlayer(model, configuration, session_id, dataset_name)
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

        session = InferenceSession(session_id, checkpoint, dataset_name, player)
        session.last_prediction = prediction
        inference_state.create_session(session)

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
        try:
            prediction = session.predict()
        except Exception as exc:
            logger.exception("Failed to compute next prediction")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to compute next prediction.",
            ) from exc

        return InferenceNextResponse(
            session_id=session_id,
            prediction=PredictionResponse(**prediction),
        )

    # -----------------------------------------------------------------------------
    def submit_step(self, session_id: str, payload: InferenceStepRequest) -> InferenceStepResponse:
        session = inference_state.get_session(session_id)
        try:
            step_payload, next_prediction = session.step(payload.extraction)
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

        return InferenceStepResponse(
            session_id=session_id,
            step=step_payload["step"],
            real_extraction=step_payload["real_extraction"],
            predicted_action=step_payload["predicted_action"],
            predicted_action_desc=step_payload["predicted_action_desc"],
            reward=step_payload["reward"],
            capital_after=step_payload["capital_after"],
            next_prediction=PredictionResponse(**next_prediction),
        )

    # -----------------------------------------------------------------------------
    def shutdown(self, session_id: str) -> InferenceShutdownResponse:
        inference_state.delete_session(session_id)
        return InferenceShutdownResponse(session_id=session_id, status="closed")

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


inference_endpoint = InferenceEndpoint(router=router)
inference_endpoint.add_routes()

