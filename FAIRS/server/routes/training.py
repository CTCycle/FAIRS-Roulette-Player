from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, WebSocket, WebSocketDisconnect, status

from FAIRS.server.schemas.training import ResumeConfig, TrainingConfig

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
        self.latest_stats: dict[str, Any] = {
            "epoch": 0,
            "total_epochs": 0,
            "time_step": 0,
            "loss": 0.0,
            "rmse": 0.0,
            "val_loss": 0.0,
            "val_rmse": 0.0,
            "reward": 0,
            "val_reward": 0.0,
            "total_reward": 0,
            "capital": 0,
            "status": "idle",
        }
        self.history_points: list[dict[str, Any]] = []
        self.max_history_points = 2000
        self.latest_env: dict[str, Any] = {}


    # -------------------------------------------------------------------------
    async def broadcast_update(self, message: dict[str, Any]) -> None:
        self.latest_stats = {**self.latest_stats, **message}
        self.add_history_point(self.latest_stats)
        await self.broadcast_message("update", self.latest_stats)

    # -------------------------------------------------------------------------
    async def broadcast_message(self, message_type: str, data: dict[str, Any]) -> None:
        for ws in self.active_websockets[:]:
            try:
                await ws.send_json({"type": message_type, "data": data})
            except Exception:
                if ws in self.active_websockets:
                    self.active_websockets.remove(ws)

    # -------------------------------------------------------------------------
    async def broadcast_env(self, payload: dict[str, Any]) -> None:
        self.latest_env = payload
        await self.broadcast_message("env", payload)

    # -------------------------------------------------------------------------
    def add_history_point(self, stats: dict[str, Any]) -> None:
        if stats.get("status") != "training":
            return
        time_step = stats.get("time_step")
        loss = stats.get("loss")
        rmse = stats.get("rmse")
        epoch = stats.get("epoch")
        if not isinstance(time_step, int):
            return
        if not isinstance(loss, (int, float)) or not isinstance(rmse, (int, float)):
            return
        if not isinstance(epoch, int):
            return
        if time_step <= 0:
            return

        point = {
            "time_step": time_step, 
            "loss": float(loss), 
            "rmse": float(rmse), 
            "val_loss": float(stats.get("val_loss", 0.0)),
            "val_rmse": float(stats.get("val_rmse", 0.0)),
            "epoch": epoch
        }
        if self.history_points and self.history_points[-1].get("time_step") == time_step:
            self.history_points[-1] = point
        else:
            self.history_points.append(point)

        if len(self.history_points) > self.max_history_points:
            self.history_points = self.history_points[-self.max_history_points:]




###############################################################################
class TrainingEndpoint:
    def __init__(self, router: APIRouter) -> None:
        self.router = router
        self.data_serializer = DataSerializerExtension()
        self.model_serializer = ModelSerializer()
        self.training_state = TrainingState()

    # -------------------------------------------------------------------------
    async def start_training(
        self,
        config: TrainingConfig,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        if self.training_state.is_training:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Training is already in progress.",
            )

        self.training_state.is_training = True

        base_config = TrainingConfig().model_dump()
        overrides = config.model_dump(exclude_unset=True)
        configuration = {**base_config, **overrides}

        self.training_state.history_points = []
        self.training_state.latest_env = {}
        background_tasks.add_task(self.run_training_task, configuration)

        return {
            "status": "started",
            "message": "Training started successfully",
            "config": configuration,
        }

    # -------------------------------------------------------------------------
    async def run_training_task(self, configuration: dict[str, Any]) -> None:
        self.training_state.is_training = True

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
            self.training_state.current_trainer = trainer
            logger.info("Start training with reinforcement learning model")

            async def ws_callback(stats: dict[str, Any]) -> None:
                await self.training_state.broadcast_update(stats)

            async def ws_env_callback(payload: dict[str, Any]) -> None:
                await self.training_state.broadcast_env(payload)

            model, history = await trainer.train_model(
                Q_model,
                target_model,
                dataset,
                checkpoint_path,
                ws_callback=ws_callback,
                ws_env_callback=ws_env_callback,
            )

            # Save model
            self.model_serializer.save_pretrained_model(model, checkpoint_path)
            self.model_serializer.save_training_configuration(
                checkpoint_path, history, configuration
            )

            # Notify completion
            await self.training_state.broadcast_update({
                "status": "completed",
                "message": "Training completed",
                "epoch": configuration.get("episodes", 10),
                "total_epochs": configuration.get("episodes", 10),
            })

            logger.info("Training completed successfully")

        except Exception as exc:
            logger.exception("Training failed")
            await self.training_state.broadcast_update({
                "status": "error",
                "message": str(exc),
            })
        finally:
            self.training_state.is_training = False
            self.training_state.current_trainer = None

    # -------------------------------------------------------------------------
    async def resume_training(
        self,
        config: ResumeConfig,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        if self.training_state.is_training:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Training is already in progress.",
            )

        self.training_state.is_training = True

        self.training_state.history_points = []
        self.training_state.latest_env = {}
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
        self.training_state.is_training = True

        try:
            logger.info(f"Loading {checkpoint_name} checkpoint")
            model, train_config, session, checkpoint_path = self.model_serializer.load_checkpoint(
                checkpoint_name
            )
            model.summary(expand_nested=True)

            # Restore previous history points from checkpoint session
            if session and "history" in session:
                prev_history = session["history"]
                prev_episodes = prev_history.get("episode", [])
                prev_time_steps = prev_history.get("time_step", [])
                prev_losses = prev_history.get("loss", [])
                prev_metrics = prev_history.get("metrics", [])
                prev_val_losses = prev_history.get("val_loss", [])
                prev_val_rmses = prev_history.get("val_rmse", [])

                restored_points = []
                for i in range(len(prev_time_steps)):
                    point = {
                        "time_step": prev_time_steps[i] if i < len(prev_time_steps) else 0,
                        "loss": float(prev_losses[i]) if i < len(prev_losses) else 0.0,
                        "rmse": float(prev_metrics[i]) if i < len(prev_metrics) else 0.0,
                        "val_loss": float(prev_val_losses[i]) if prev_val_losses and i < len(prev_val_losses) else 0.0,
                        "val_rmse": float(prev_val_rmses[i]) if prev_val_rmses and i < len(prev_val_rmses) else 0.0,
                        "epoch": prev_episodes[i] if i < len(prev_episodes) else 0,
                    }
                    restored_points.append(point)

                self.training_state.history_points = restored_points
                logger.info(f"Restored {len(restored_points)} history points from checkpoint")
            else:
                self.training_state.history_points = []

            self.training_state.latest_env = {}

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
            trainer = DQNTraining(train_config, session=session)
            self.training_state.current_trainer = trainer
            logger.info("Resuming training with reinforcement learning model")

            async def ws_callback(stats: dict[str, Any]) -> None:
                await self.training_state.broadcast_update(stats)

            async def ws_env_callback(payload: dict[str, Any]) -> None:
                await self.training_state.broadcast_env(payload)

            model, history = await trainer.resume_training(
                model,
                model,  # Use same model as target for resume
                dataset,
                checkpoint_path,
                session,
                additional_episodes,
                ws_callback=ws_callback,
                ws_env_callback=ws_env_callback,
            )

            # Save model
            self.model_serializer.save_pretrained_model(model, checkpoint_path)
            self.model_serializer.save_training_configuration(
                checkpoint_path, history, train_config
            )

            await self.training_state.broadcast_update({
                "status": "completed",
                "message": "Resume training completed",
            })

            logger.info("Resume training completed successfully")

        except Exception as exc:
            logger.exception("Resume training failed")
            await self.training_state.broadcast_update({
                "status": "error",
                "message": str(exc),
            })
        finally:
            self.training_state.is_training = False
            self.training_state.current_trainer = None

    # -------------------------------------------------------------------------
    def get_status(self) -> dict[str, Any]:
        return {
            "is_training": self.training_state.is_training,
            "latest_stats": self.training_state.latest_stats,
            "history": self.training_state.history_points,
            "latest_env": self.training_state.latest_env,
            "active_connections": len(self.training_state.active_websockets),
            "active_connections": len(self.training_state.active_websockets),
        }



    # -------------------------------------------------------------------------
    def stop_training(self) -> dict[str, Any]:
        if not self.training_state.is_training:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No training is in progress.",
            )

        if self.training_state.current_trainer:
            self.training_state.current_trainer.cancel_training()

        return {"status": "stopping", "message": "Training stop requested"}

    # -------------------------------------------------------------------------
    def get_checkpoints(self) -> list[str]:
        return self.model_serializer.scan_checkpoints_folder()

    # -------------------------------------------------------------------------
    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.training_state.active_websockets.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.training_state.active_websockets)}")

        try:
            # Send initial state
            await websocket.send_json({
                "type": "connection",
                "data": {
                    "is_training": self.training_state.is_training,
                    "latest_stats": self.training_state.latest_stats,

                    "history": self.training_state.history_points,
                    "latest_env": self.training_state.latest_env,
                }
            })

            # Keep connection alive
            while True:
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
                except asyncio.TimeoutError:
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        break

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as exc:
            logger.warning(f"WebSocket error: {exc}")
        finally:
            if websocket in self.training_state.active_websockets:
                self.training_state.active_websockets.remove(websocket)
            logger.info(f"WebSocket removed. Total connections: {len(self.training_state.active_websockets)}")

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
        self.router.add_api_websocket_route("/ws", self.websocket_endpoint)


training_endpoint = TrainingEndpoint(router=router)
training_endpoint.add_routes()
