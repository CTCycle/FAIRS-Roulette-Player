from __future__ import annotations

from typing import Any

import cv2
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PySide6.QtGui import QImage, QPixmap

from FAIRS.app.client.workers import ProcessWorker, ThreadWorker, check_thread_status
from FAIRS.app.utils.learning.device import DeviceConfig
from FAIRS.app.utils.learning.inference.player import RoulettePlayer
from FAIRS.app.utils.learning.models.qnet import FAIRSnet
from FAIRS.app.utils.learning.training.fitting import DQNTraining
from FAIRS.app.utils.logger import logger
from FAIRS.app.utils.repository.serializer import DataSerializer, ModelSerializer
from FAIRS.app.utils.services.process import RouletteSeriesEncoder
from FAIRS.app.utils.validation.checkpoints import ModelEvaluationSummary
from FAIRS.app.utils.validation.dataset import RouletteSeriesValidation


###############################################################################
class GraphicsHandler:
    def __init__(self) -> None:
        self.image_encoding = cv2.IMREAD_UNCHANGED
        self.gray_scale_encoding = cv2.IMREAD_GRAYSCALE
        self.BGRA_encoding = cv2.COLOR_BGRA2RGBA
        self.BGR_encoding = cv2.COLOR_BGR2RGB

    # -------------------------------------------------------------------------
    def convert_fig_to_qpixmap(self, fig: Figure) -> QPixmap:
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        # get the size in pixels and initialize raw RGBA buffer
        width, height = canvas.get_width_height()
        buf = canvas.buffer_rgba()
        # construct a QImage pointing at that memory (no PNG decoding)
        qimg = QImage(buf, width, height, QImage.Format.Format_RGBA8888)

        return QPixmap.fromImage(qimg)

    # -------------------------------------------------------------------------
    def load_image_as_pixmap(self, path: str) -> QPixmap:
        img = cv2.imread(path, self.image_encoding)
        # Handle grayscale, RGB, or RGBA
        if len(img.shape) == 2:  # Grayscale
            img = cv2.cvtColor(img, self.gray_scale_encoding)
        elif img.shape[2] == 4:  # BGRA
            img = cv2.cvtColor(img, self.BGRA_encoding)
        else:  # BGR
            img = cv2.cvtColor(img, self.BGR_encoding)

        h, w = img.shape[:2]
        if img.shape[2] == 3:
            qimg = QImage(img.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        else:
            qimg = QImage(img.data, w, h, 4 * w, QImage.Format.Format_RGBA8888)

        return QPixmap.fromImage(qimg)


###############################################################################
class ValidationEvents:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.serializer = DataSerializer()
        self.modser = ModelSerializer()
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def run_dataset_evaluation_pipeline(
        self, metrics: list[str], progress_callback: Any | None = None, worker=None
    ) -> list[Any]:
        seed = self.configuration.get("seed", 42)
        sample_size = self.configuration.get("sample_size", 1.0)
        roulette_data = self.serializer.load_roulette_dataset(sample_size, seed)
        logger.info(
            f"The loaded roulette series includes {len(roulette_data)} extractions"
        )
        validator = RouletteSeriesValidation(self.configuration)

        metric_map = {
            "roulette_transitions": validator.roulette_transitions,
        }

        images = []
        for metric in metrics:
            if metric in metric_map:
                # check worker status to allow interruption
                check_thread_status(worker)
                metric_name = metric.replace("_", " ").title()
                logger.info(f"Current metric: {metric_name}")
                result = metric_map[metric](
                    roulette_data,
                    metric_name=metric,
                    progress_callback=progress_callback,
                    worker=worker,
                )
                images.append(result)

        return images

    # -------------------------------------------------------------------------
    def get_checkpoints_summary(
        self,
        progress_callback: Any | None = None,
        worker: ThreadWorker | ProcessWorker | None = None,
    ) -> None:
        summarizer = ModelEvaluationSummary(self.configuration)
        checkpoints_summary = summarizer.get_checkpoints_summary(
            progress_callback=progress_callback, worker=worker
        )

        logger.info(
            f"Checkpoints summary has been created for {checkpoints_summary.shape[0]} models"
        )

    # -------------------------------------------------------------------------
    def run_model_evaluation_pipeline(
        self,
        metrics: list[str],
        selected_checkpoint: str,
        progress_callback: Any | None = None,
        worker=None,
    ) -> list[Any]:
        logger.info(f"Loading {selected_checkpoint} checkpoint")
        model, train_config, _, _ = self.modser.load_checkpoint(selected_checkpoint)
        model.summary(expand_nested=True)

        # setting device for training
        device = DeviceConfig(self.configuration)
        device.set_device()

        # select images from the inference folder and retrieve current paths
        seed = train_config.get("seed", 42)
        sample_size = self.configuration.get("sample_size", 1.0)
        dataset = self.serializer.load_roulette_dataset(sample_size, seed)
        logger.info(f"Roulette series has been loaded ({len(dataset)} extractions)")
        # use the mapper to encode extractions based on position and color
        mapper = RouletteSeriesEncoder(self.configuration)
        logger.info("Encoding roulette extractions")
        dataset = mapper.encode_roulette_series(dataset)

        # evaluate model performance over the training and validation dataset
        summarizer = ModelEvaluationSummary(self.configuration, model)

        metric_map = {
            # TO DO: must pass a series of perceptive fields as input
            # create a method in data/loader.py that mimics dataloader from other projects
            "evaluation_report": summarizer.get_evaluation_report
        }

        images = []
        for metric in metrics:
            if metric in metric_map:
                # check worker status to allow interruption
                check_thread_status(worker)
                metric_name = metric.replace("_", " ").title()
                logger.info(f"Current metric: {metric_name}")
                result = metric_map[metric](
                    dataset, progress_callback=progress_callback, worker=worker
                )
                images.append(result)

        return images


###############################################################################
class ModelEvents:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.serializer = DataSerializer()
        self.modser = ModelSerializer()
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def get_available_checkpoints(self) -> list[str]:
        return self.modser.scan_checkpoints_folder()

    # -------------------------------------------------------------------------
    def run_training_pipeline(
        self,
        progress_callback: Any | None = None,
        worker: ThreadWorker | ProcessWorker | None = None,
    ) -> None:
        dataset, synthetic = self.serializer.get_training_series(self.configuration)
        if synthetic:
            logger.info(
                f"Synthetic roulette series generated ({len(dataset)} extractions)"
            )
        else:
            logger.info(f"Roulette series has been loaded ({len(dataset)} extractions)")
        # use the mapper to encode extractions based on position and color
        mapper = RouletteSeriesEncoder(self.configuration)
        logger.info("Encoding roulette extractions")
        dataset = mapper.encode_roulette_series(dataset)
        if not synthetic:
            self.serializer.save_roulette_dataset(dataset)
            logger.info("Database updated with processed roulette series")

        # check worker status to allow interruption
        check_thread_status(worker)

        # set device for training operations
        logger.info("Setting device for training operations")
        device = DeviceConfig(self.configuration)
        device.set_device()

        # create checkpoint folder
        checkpoint_path = self.modser.create_checkpoint_folder()
        # build the target model and Q model based on FAIRSnet specifics
        # Q model is the main trained model, while target model is used to predict
        # next state Q scores and is updated based on the Q model weights
        logger.info("Building FAIRS reinforcement learning model")
        learner = FAIRSnet(self.configuration)
        Q_model = learner.get_model(model_summary=True)
        target_model = learner.get_model(model_summary=False)

        # perform training and save model at the end
        trainer = DQNTraining(self.configuration)
        logger.info("Start training with reinforcement learning model")
        model, history = trainer.train_model(
            Q_model,
            target_model,
            dataset,
            checkpoint_path,
            progress_callback=progress_callback,
            worker=worker,
        )

        # Save the final model at the end of training
        self.modser.save_pretrained_model(model, checkpoint_path)
        self.modser.save_training_configuration(
            checkpoint_path, history, self.configuration
        )

    # -------------------------------------------------------------------------
    def resume_training_pipeline(
        self,
        selected_checkpoint: str,
        progress_callback: Any | None = None,
        worker=None,
    ) -> None:
        logger.info(f"Loading {selected_checkpoint} checkpoint")
        model, train_config, session, checkpoint_path = self.modser.load_checkpoint(
            selected_checkpoint
        )
        model.summary(expand_nested=True)

        # set device for training operations
        logger.info("Setting device for training operations")
        device = DeviceConfig(self.configuration)
        device.set_device()

        # process dataset using model configurations
        resume_config = dict(self.configuration)
        resume_config["use_data_generator"] = resume_config.get(
            "use_data_generator", False
        ) or train_config.get("use_data_generator", False)
        dataset, synthetic = self.serializer.get_training_series(resume_config)
        if synthetic:
            logger.info(
                f"Synthetic roulette series generated ({len(dataset)} extractions)"
            )
        else:
            logger.info(f"Roulette series has been loaded ({len(dataset)} extractions)")

        # use the mapper to encode extractions based on position and color
        mapper = RouletteSeriesEncoder(train_config)
        logger.info("Encoding roulette extractions")
        dataset = mapper.encode_roulette_series(dataset)

        # check worker status to allow interruption
        check_thread_status(worker)

        # perform training and save model at the end
        trainer = DQNTraining(train_config)
        logger.info("Start training with reinforcement learning model")
        additional_epochs = self.configuration.get("additional_episodes", 10)
        model, history = trainer.resume_training(
            model,
            model,
            dataset,
            checkpoint_path,
            session,
            additional_epochs,
            progress_callback=progress_callback,
            worker=worker,
        )

        # Save the final model at the end of training
        self.modser.save_pretrained_model(model, checkpoint_path)
        self.modser.save_training_configuration(checkpoint_path, history, train_config)

    # -------------------------------------------------------------------------
    # this is implemented as static method as it is run by a model window.
    # the inference pipeline is run by a process worker that sends signals to the dialog box
    # -------------------------------------------------------------------------
    @staticmethod
    def run_inference_pipeline(
        configuration: dict[str, Any], checkpoint_name: str, cmd_q, out_q
    ) -> None:
        """
        Child-process loop for real-time inference through external dialog window:
          - build the model and RoulettePlayer locally
          - react to dict commands from cmd_q
          - emit dict events on out_q

        Events:
          {"kind":"prediction", "action": int, "description": str}
          {"kind":"updated", "value": int}
          {"kind":"error", "detail": str}
          {"kind":"closed"}

        """
        logger.info(f"Loading {checkpoint_name} checkpoint")
        modser = ModelSerializer()
        model, train_config, _, _ = modser.load_checkpoint(checkpoint_name)
        model.summary(expand_nested=True)

        # Ensure device is set in the child process (so GPU context is owned here)
        logger.info("Setting device for inference operations")
        device = DeviceConfig(configuration)
        device.set_device()

        # Load the data you will use to seed the perceptive field.
        # The player expects raw extractions in [0, 36] as ints.
        dataserializer = DataSerializer()
        dataset = dataserializer.load_inference_dataset()
        # dataset is expected as an array-like with at least one column where [:,0] are extractions
        if dataset.empty:
            return

        # Build player with training-time agent settings
        player = RoulettePlayer(model, train_config)
        logger.info(
            "Perceptive field is being created from the most recent inference data window"
        )
        player.initialize_states()

        # Signal to parent process: model & data are loaded, ready for commands
        out_q.put({"kind": "ready"})
        running = True
        logger.info("Starting real-time inference session")
        while running:
            cmd = cmd_q.get()  # blocking; dedicated process
            kind = cmd["kind"]
            if kind == "next":
                try:
                    res = player.predict_next()
                    out_q.put({"kind": "prediction", **res})
                except Exception as e:
                    out_q.put({"kind": "error", "detail": f"predict failed: {e!r}"})

            elif kind == "update":
                try:
                    value = cmd.get("value", None)
                    if value is None:
                        return
                    ivalue = int(value)
                    if not (0 <= ivalue <= 36):
                        raise ValueError("Inserted value should be between 0 and 36")
                    player.update_with_true_extraction(ivalue)
                    player.save_prediction(checkpoint_name)
                    out_q.put({"kind": "updated", "value": ivalue})
                except Exception as e:
                    out_q.put({"kind": "error", "detail": f"update failed: {e!r}"})

            elif kind == "shutdown":
                running = False
                out_q.put({"kind": "closed"})
                break

            else:
                out_q.put({"kind": "error", "detail": f"unknown command: {kind}"})
