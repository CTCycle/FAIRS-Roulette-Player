from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, WebSocket, WebSocketDisconnect, status

from FAIRS.server.schemas.training import TrainingConfig, ResumeConfig

from FAIRS.server.utils.configurations import server_settings
from FAIRS.server.utils.logger import logger
from FAIRS.server.utils.services.training.device import DeviceConfig
from FAIRS.server.utils.services.training.fitting import DQNTraining
from FAIRS.server.utils.services.training.models.qnet import FAIRSnet
from FAIRS.server.utils.services.training.serializer import DataSerializerExtension, ModelSerializer


router = APIRouter(prefix="/training", tags=["training"])


###############################################################################
class TrainingState:
    def __init__(self) -> None:
        self.is_training = False
        self.current_trainer: DQNTraining | None = None
        self.active_websockets: list[WebSocket] = []
        self.latest_stats: dict[str, Any] = {}

    async def broadcast(self, message: dict[str, Any]) -> None:
        self.latest_stats = message
        for ws in self.active_websockets[:]:
            try:
                await ws.send_json({"type": "update", "data": message})
            except Exception:
                self.active_websockets.remove(ws)


training_state = TrainingState()


###############################################################################
class TrainingEndpoint:
    def __init__(self, router: APIRouter) -> None:
        self.router = router
        self.data_serializer = DataSerializerExtension()
        self.model_serializer = ModelSerializer()

    # -------------------------------------------------------------------------
    async def start_training(
        self,
        config: TrainingConfig,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        if training_state.is_training:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Training is already in progress.",
            )

        configuration = config.model_dump()
        background_tasks.add_task(self.run_training_task, configuration)

        return {
            "status": "started",
            "message": "Training started successfully",
            "config": configuration,
        }

    # -------------------------------------------------------------------------
    async def run_training_task(self, configuration: dict[str, Any]) -> None:
        training_state.is_training = True

        try:
            logger.info("Starting training pipeline")

            # Load dataset
            dataset, synthetic = self.data_serializer.get_training_series(configuration)
            if synthetic:
                logger.info(
                    f"Synthetic roulette series generated ({len(dataset)} extractions)"
                )
            else:
                logger.info(f"Roulette series has been loaded ({len(dataset)} extractions)")

            # Set device
            logger.info("Setting device for training operations")
            device = DeviceConfig(configuration)
            device.set_device()

            # Create checkpoint folder
            checkpoint_path = self.model_serializer.create_checkpoint_folder()

            # Build models
            logger.info("Building FAIRS reinforcement learning model")
            learner = FAIRSnet(configuration)
            Q_model = learner.get_model(model_summary=True)
            target_model = learner.get_model(model_summary=False)

            # Train
            trainer = DQNTraining(configuration)
            training_state.current_trainer = trainer
            logger.info("Start training with reinforcement learning model")

            async def ws_callback(stats: dict[str, Any]) -> None:
                await training_state.broadcast(stats)

            model, history = await trainer.train_model(
                Q_model,
                target_model,
                dataset,
                checkpoint_path,
                ws_callback=ws_callback,
            )

            # Save model
            self.model_serializer.save_pretrained_model(model, checkpoint_path)
            self.model_serializer.save_training_configuration(
                checkpoint_path, history, configuration
            )

            # Notify completion
            await training_state.broadcast({
                "epoch": configuration.get("episodes", 10),
                "total_epochs": configuration.get("episodes", 10),
                "time_step": 0,
                "loss": history["history"]["loss"][-1] if history["history"]["loss"] else 0,
                "rmse": history["history"]["metrics"][-1] if history["history"]["metrics"] else 0,
                "reward": 0,
                "total_reward": 0,
                "capital": 0,
                "status": "completed",
            })

            logger.info("Training completed successfully")

        except Exception as exc:
            logger.exception("Training failed")
            await training_state.broadcast({
                "status": "error",
                "message": str(exc),
            })
        finally:
            training_state.is_training = False
            training_state.current_trainer = None

    # -------------------------------------------------------------------------
    async def resume_training(
        self,
        config: ResumeConfig,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        if training_state.is_training:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Training is already in progress.",
            )

        background_tasks.add_task(
            self.run_resume_task, config.checkpoint, config.additional_episodes
        )

        return {
            "status": "started",
            "message": f"Resuming training from {config.checkpoint}",
            "checkpoint": config.checkpoint,
            "additional_episodes": config.additional_episodes,
        }

    # -------------------------------------------------------------------------
    async def run_resume_task(
        self, checkpoint_name: str, additional_episodes: int
    ) -> None:
        training_state.is_training = True

        try:
            logger.info(f"Loading {checkpoint_name} checkpoint")
            model, train_config, session, checkpoint_path = self.model_serializer.load_checkpoint(
                checkpoint_name
            )
            model.summary(expand_nested=True)

            # Set device
            logger.info("Setting device for training operations")
            device = DeviceConfig(train_config)
            device.set_device()

            # Load dataset
            dataset, synthetic = self.data_serializer.get_training_series(train_config)
            if synthetic:
                logger.info(
                    f"Synthetic roulette series generated ({len(dataset)} extractions)"
                )
            else:
                logger.info(f"Roulette series has been loaded ({len(dataset)} extractions)")

            # Train
            trainer = DQNTraining(train_config)
            training_state.current_trainer = trainer
            logger.info("Resuming training with reinforcement learning model")

            async def ws_callback(stats: dict[str, Any]) -> None:
                await training_state.broadcast(stats)

            model, history = await trainer.resume_training(
                model,
                model,  # Use same model as target for resume
                dataset,
                checkpoint_path,
                session,
                additional_episodes,
                ws_callback=ws_callback,
            )

            # Save model
            self.model_serializer.save_pretrained_model(model, checkpoint_path)
            self.model_serializer.save_training_configuration(
                checkpoint_path, history, train_config
            )

            await training_state.broadcast({
                "status": "completed",
                "message": "Resume training completed",
            })

            logger.info("Resume training completed successfully")

        except Exception as exc:
            logger.exception("Resume training failed")
            await training_state.broadcast({
                "status": "error",
                "message": str(exc),
            })
        finally:
            training_state.is_training = False
            training_state.current_trainer = None

    # -------------------------------------------------------------------------
    def get_status(self) -> dict[str, Any]:
        return {
            "is_training": training_state.is_training,
            "latest_stats": training_state.latest_stats,
            "active_connections": len(training_state.active_websockets),
        }

    # -------------------------------------------------------------------------
    def stop_training(self) -> dict[str, Any]:
        if not training_state.is_training:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No training is in progress.",
            )

        if training_state.current_trainer:
            training_state.current_trainer.cancel_training()

        return {"status": "stopping", "message": "Training stop requested"}

    # -------------------------------------------------------------------------
    def get_checkpoints(self) -> list[str]:
        return self.model_serializer.scan_checkpoints_folder()

    # -------------------------------------------------------------------------
    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        await websocket.accept()
        training_state.active_websockets.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(training_state.active_websockets)}")

        try:
            # Send initial state
            await websocket.send_json({
                "type": "connection",
                "data": {
                    "is_training": training_state.is_training,
                    "latest_stats": training_state.latest_stats,
                }
            })

            # Keep connection alive
            while True:
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "ping"})

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as exc:
            logger.warning(f"WebSocket error: {exc}")
        finally:
            if websocket in training_state.active_websockets:
                training_state.active_websockets.remove(websocket)
            logger.info(f"WebSocket removed. Total connections: {len(training_state.active_websockets)}")

    # -------------------------------------------------------------------------
    def add_routes(self) -> None:
        self.router.add_api_route(
            "/start",
            self.start_training,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/resume",
            self.resume_training,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/status",
            self.get_status,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/stop",
            self.stop_training,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/checkpoints",
            self.get_checkpoints,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_websocket_route("/ws", self.websocket_endpoint)


training_endpoint = TrainingEndpoint(router=router)
training_endpoint.add_routes()
