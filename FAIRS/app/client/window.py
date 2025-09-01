from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pandas as pd

from FAIRS.app.variables import EnvironmentVariables

EV = EnvironmentVariables()

from functools import partial

from PySide6.QtCore import QFile, QIODevice, Qt, QThreadPool, QTimer, Slot
from PySide6.QtGui import QAction, QPainter, QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
)
from qt_material import apply_stylesheet

from FAIRS.app.client.dialogs import LoadConfigDialog, RouletteDialog, SaveConfigDialog
from FAIRS.app.client.events import GraphicsHandler, ModelEvents, ValidationEvents
from FAIRS.app.client.workers import ProcessWorker, ThreadWorker
from FAIRS.app.configuration import Configuration
from FAIRS.app.logger import logger
from FAIRS.app.utils.data.database import database


###############################################################################
def apply_style(app: QApplication) -> QApplication:
    theme = "dark_yellow"
    extra = {"density_scale": "-1"}
    apply_stylesheet(app, theme=f"{theme}.xml", extra=extra)

    # Make % text visible/centered for ALL progress bars
    app.setStyleSheet(
        app.styleSheet()
        + """
    QProgressBar {
        text-align: center;  /* align percentage to the center */
        color: black;        /* black text for yellow bar */
        font-weight: bold;   /* bold percentage */        
    }
    """
    )

    return app


###############################################################################
class MainWindow:
    def __init__(self, ui_file_path: str) -> None:
        super().__init__()
        loader = QUiLoader()
        ui_file = QFile(ui_file_path)
        ui_file.open(QIODevice.OpenModeFlag.ReadOnly)
        self.main_win = cast(QMainWindow, loader.load(ui_file))
        ui_file.close()

        # Checkpoint & metrics state
        self.checkpoints_list: QComboBox
        self.selected_checkpoint = None
        self.selected_metrics = {"dataset": [], "model": []}

        # initial settings
        self.config_manager = Configuration()
        self.configuration = self.config_manager.get_configuration()

        # set thread pool for the workers
        self.threadpool = QThreadPool.globalInstance()
        self.worker: ThreadWorker | ProcessWorker | None = None

        # initialize database
        database.initialize_database()

        # --- Create persistent handlers ---
        self.graphic_handler = GraphicsHandler()
        self.validation_handler = ValidationEvents(self.configuration)
        self.model_handler = ModelEvents(self.configuration)

        # setup UI elements
        self._set_states()
        self.widgets = {}
        self._setup_configuration(
            [
                # actions
                (QAction, "actionLoadConfig", "load_configuration_action"),
                (QAction, "actionSaveConfig", "save_configuration_action"),
                (QAction, "actionDeleteData", "delete_data_action"),
                (QAction, "actionExportData", "export_data_action"),
                # out of tab widgets
                (QProgressBar, "progressBar", "progress_bar"),
                (QPushButton, "stopThread", "stop_thread"),
                # data source group
                (QPushButton, "loadData", "load_dataset"),
                (QDoubleSpinBox, "sampleSize", "sample_size"),
                (QSpinBox, "seed", "seed"),
                # 1. dataset tab page
                (QCheckBox, "rouletteTransitions", "roulette_transitions_metric"),
                (QPushButton, "evaluateDataset", "evaluate_dataset"),
                # 2. training tab page
                # dataset settings group
                (QCheckBox, "useDataGen", "use_data_generator"),
                (QDoubleSpinBox, "trainSampleSize", "train_sample_size"),
                (QDoubleSpinBox, "validationSize", "validation_size"),
                (QSpinBox, "splitSeed", "split_seed"),
                (QCheckBox, "setShuffle", "use_shuffle"),
                (QSpinBox, "shuffleSize", "shuffle_size"),
                # training settings group
                (QSpinBox, "trainSeed", "train_seed"),
                (QSpinBox, "numEpisodes", "episodes"),
                (QSpinBox, "maxStepsEp", "max_steps_episode"),
                (QSpinBox, "batchSize", "batch_size"),
                (QDoubleSpinBox, "learningRate", "learning_rate"),
                (QCheckBox, "mixedPrecision", "use_mixed_precision"),
                (QCheckBox, "compileJIT", "use_JIT_compiler"),
                (QComboBox, "backendJIT", "jit_backend"),
                (QSpinBox, "saveCPFrequency", "checkpoints_frequency"),
                (QSpinBox, "maxMemorySize", "max_memory_size"),
                (QSpinBox, "replayBuffer", "replay_buffer_size"),
                (QCheckBox, "runTensorboard", "use_tensorboard"),
                (QCheckBox, "realTimeHistory", "real_time_history_callback"),
                (QCheckBox, "saveCheckpoints", "save_checkpoints"),
                # agent settings group
                (QSpinBox, "numNeurons", "QNet_neurons"),
                (QSpinBox, "perceptiveField", "perceptive_field_size"),
                (QSpinBox, "embeddingDims", "embedding_dimensions"),
                (QDoubleSpinBox, "explorationRate", "exploration_rate"),
                (QDoubleSpinBox, "minExplorationRate", "min_exploration_rate"),
                (QDoubleSpinBox, "explorationRateDecay", "exploration_rate_decay"),
                (QDoubleSpinBox, "discountRate", "discount_rate"),
                (QSpinBox, "modelUpdateFreq", "model_update_frequency"),
                # environment
                (QSpinBox, "initialCapital", "initial_capital"),
                (QSpinBox, "betAmount", "bet_amount"),
                (QCheckBox, "renderEnv", "render_environment"),
                # session settings group
                (QCheckBox, "deviceGPU", "use_device_GPU"),
                (QSpinBox, "deviceID", "device_ID"),
                (QSpinBox, "numWorkers", "num_workers"),
                (QSpinBox, "numAdditionalEpisodes", "additional_episodes"),
                (QPushButton, "startTraining", "start_training"),
                (QPushButton, "resumeTraining", "resume_training"),
                # model inference and evaluation
                (QPushButton, "refreshCheckpoints", "refresh_checkpoints"),
                (QComboBox, "checkpointsList", "checkpoints_list"),
                (QSpinBox, "inferenceBatchSize", "inference_batch_size"),
                (QSpinBox, "initInferenceCap", "game_capital"),
                (QSpinBox, "playBet", "game_bet"),
                (QPushButton, "playRoulette", "start_roulette_game"),
                (QSpinBox, "evalSamples", "num_evaluation_samples"),
                (QCheckBox, "evalReport", "get_evaluation_report"),
                (QCheckBox, "classAccuracy", "classification_accuracy"),
                (QPushButton, "evaluateModel", "model_evaluation"),
                (QPushButton, "checkpointSummary", "checkpoints_summary"),
                # 3. Viewer tab
                (QPushButton, "previousImg", "previous_image"),
                (QPushButton, "nextImg", "next_image"),
                (QPushButton, "clearImg", "clear_images"),
            ]
        )

        self._connect_signals(
            [
                # actions
                ("save_configuration_action", "triggered", self.save_configuration),
                ("load_configuration_action", "triggered", self.load_configuration),
                ("delete_data_action", "triggered", self.delete_all_data),
                ("export_data_action", "triggered", self.export_all_data),
                # out of tab widgets
                ("stop_thread", "clicked", self.stop_running_worker),
                # 1. dataset tab page
                ("load_dataset", "clicked", self.update_database_from_source),
                ("roulette_transitions_metric", "toggled", self._update_metrics),
                ("evaluate_dataset", "clicked", self.run_dataset_evaluation_pipeline),
                # 2. training tab page
                ("start_training", "clicked", self.train_from_scratch),
                ("resume_training", "clicked", self.resume_training_from_checkpoint),
                # 3. model evaluation tab and inference page
                ("checkpoints_list", "currentTextChanged", self.select_checkpoint),
                ("refresh_checkpoints", "clicked", self.load_checkpoints),
                ("get_evaluation_report", "toggled", self._update_metrics),
                ("model_evaluation", "clicked", self.run_model_evaluation_pipeline),
                ("checkpoints_summary", "clicked", self.get_checkpoints_summary),
                ("start_roulette_game", "clicked", self.play_roulette),
                # 4. viewer tab page
                ("previous_image", "clicked", self.show_previous_figure),
                ("next_image", "clicked", self.show_next_figure),
                ("clear_images", "clicked", self.clear_figures),
            ]
        )

        self._auto_connect_settings()
        # Initial population of dynamic UI elements
        self.load_checkpoints()
        self._set_graphics()

    # --------------------------------------------------------------------------
    def __getattr__(self, name: str) -> Any:
        try:
            return self.widgets[name]
        except (AttributeError, KeyError) as e:
            raise AttributeError(
                f"{type(self).__name__!s} has no attribute {name!r}"
            ) from e

    # [SHOW WINDOW]
    ###########################################################################
    def show(self) -> None:
        self.main_win.show()

    # [HELPERS]
    ###########################################################################
    def connect_update_setting(
        self, widget: Any, signal_name: str, config_key: str, getter: Any | None = None
    ) -> None:
        if getter is None:
            if isinstance(widget, (QCheckBox, QRadioButton)):
                getter = widget.isChecked
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                getter = widget.value
            elif isinstance(widget, QComboBox):
                getter = widget.currentText

        signal = getattr(widget, signal_name)
        signal.connect(partial(self._update_single_setting, config_key, getter))

    # -------------------------------------------------------------------------
    def _update_single_setting(self, config_key: str, getter: Any, *args) -> None:
        value = getter()
        self.config_manager.update_value(config_key, value)

    # -------------------------------------------------------------------------
    def _auto_connect_settings(self) -> None:
        connections = [
            # 1. dataset tab page
            # dataset evaluation and processing group
            ("seed", "valueChanged", "seed"),
            ("sample_size", "valueChanged", "sample_size"),
            # 2. model tab page
            # # dataset settings group
            ("use_data_generator", "toggled", "use_data_generator"),
            ("use_shuffle", "toggled", "shuffle_dataset"),
            ("shuffle_size", "valueChanged", "shuffle_size"),
            ("train_sample_size", "valueChanged", "train_sample_size"),
            ("validation_size", "valueChanged", "validation_size"),
            ("split_seed", "valueChanged", "split_seed"),
            # device settings group
            ("use_device_GPU", "toggled", "use_device_GPU"),
            ("device_ID", "valueChanged", "device_id"),
            ("num_workers", "valueChanged", "num_workers"),
            # training settings group
            ("train_seed", "valueChanged", "train_seed"),
            ("episodes", "valueChanged", "episodes"),
            ("max_steps_episode", "valueChanged", "max_steps_episode"),
            ("batch_size", "valueChanged", "batch_size"),
            ("learning_rate", "valueChanged", "learning_rate"),
            ("use_mixed_precision", "toggled", "use_mixed_precision"),
            ("use_JIT_compiler", "toggled", "use_JIT_compiler"),
            ("jit_backend", "currentTextChanged", "jit_backend"),
            ("use_tensorboard", "toggled", "use_tensorboard"),
            ("real_time_history_callback", "toggled", "real_time_history_callback"),
            ("save_checkpoints", "toggled", "save_checkpoints"),
            ("checkpoints_frequency", "valueChanged", "checkpoints_frequency"),
            ("max_memory_size", "valueChanged", "max_memory_size"),
            ("replay_buffer_size", "valueChanged", "replay_buffer_size"),
            # agent settings group
            ("QNet_neurons", "valueChanged", "QNet_neurons"),
            ("perceptive_field_size", "valueChanged", "perceptive_field_size"),
            ("embedding_dimensions", "valueChanged", "embedding_dimensions"),
            ("exploration_rate", "valueChanged", "exploration_rate"),
            ("min_exploration_rate", "valueChanged", "min_exploration_rate"),
            ("exploration_rate_decay", "valueChanged", "exploration_rate_decay"),
            ("discount_rate", "valueChanged", "discount_rate"),
            ("model_update_frequency", "valueChanged", "model_update_frequency"),
            # environment settings group
            ("render_environment", "toggled", "render_environment"),
            ("initial_capital", "valueChanged", "initial_capital"),
            ("bet_amount", "valueChanged", "bet_amount"),
            # session settings group
            ("additional_episodes", "valueChanged", "additional_episodes"),
            # model inference and evaluation
            ("inference_batch_size", "valueChanged", "inference_batch_size"),
            ("game_capital", "valueChanged", "game_capital"),
            ("game_bet", "valueChanged", "game_bet"),
            ("num_evaluation_samples", "valueChanged", "num_evaluation_samples"),
        ]

        self.data_metrics = [("roulette_transitions", self.roulette_transitions_metric)]
        self.model_metrics = [("evaluation_report", self.get_evaluation_report)]

        for attr, signal_name, config_key in connections:
            widget = self.widgets[attr]
            self.connect_update_setting(widget, signal_name, config_key)

    # -------------------------------------------------------------------------
    def _set_states(self) -> None:
        self.progress_bar = self.main_win.findChild(QProgressBar, "progressBar")
        self.progress_bar.setValue(0) if self.progress_bar else None

    # -------------------------------------------------------------------------
    def _set_graphics(self) -> None:
        view = self.main_win.findChild(QGraphicsView, "canvas")
        scene = QGraphicsScene()
        pixmap_item = QGraphicsPixmapItem()
        pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        scene.addItem(pixmap_item)
        view.setScene(scene) if view else None
        for hint in (
            QPainter.RenderHint.Antialiasing,
            QPainter.RenderHint.SmoothPixmapTransform,
            QPainter.RenderHint.TextAntialiasing,
        ):
            if view:
                view.setRenderHint(hint, True)

        self.graphics = {"view": view, "scene": scene, "pixmap_item": pixmap_item}
        self.pixmaps = []
        self.current_fig = 0

    # -------------------------------------------------------------------------
    def _connect_button(self, button_name: str, slot: Any) -> None:
        button = self.main_win.findChild(QPushButton, button_name)
        button.clicked.connect(slot) if button else None

    # -------------------------------------------------------------------------
    def _connect_combo_box(self, combo_name: str, slot: Any) -> None:
        combo = self.main_win.findChild(QComboBox, combo_name)
        combo.currentTextChanged.connect(slot) if combo else None

    # -------------------------------------------------------------------------
    def _start_thread_worker(
        self,
        worker: ThreadWorker,
        on_finished: Callable,
        on_error: Callable,
        on_interrupted: Callable,
        update_progress: bool = True,
    ) -> None:
        if update_progress and self.progress_bar:
            self.progress_bar.setValue(0) if self.progress_bar else None
            worker.signals.progress.connect(self.progress_bar.setValue)
        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        worker.signals.interrupted.connect(on_interrupted)
        self.threadpool.start(worker)

    # -------------------------------------------------------------------------
    def _start_process_worker(
        self,
        worker: ProcessWorker,
        on_finished: Callable,
        on_error: Callable,
        on_interrupted: Callable,
        update_progress: bool = True,
    ) -> None:
        if update_progress and self.progress_bar:
            self.progress_bar.setValue(0) if self.progress_bar else None
            worker.signals.progress.connect(self.progress_bar.setValue)

        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        worker.signals.interrupted.connect(on_interrupted)

        # Polling for results from the process queue
        self.process_worker_timer = QTimer()
        self.process_worker_timer.setInterval(100)
        self.process_worker_timer.timeout.connect(worker.poll)
        worker._timer = self.process_worker_timer
        self.process_worker_timer.start()

        worker.start()

    # -------------------------------------------------------------------------
    def _send_message(self, message) -> None:
        self.main_win.statusBar().showMessage(message)

    # [SETUP]
    ###########################################################################
    def _setup_configuration(self, widget_defs) -> None:
        for cls, name, attr in widget_defs:
            w = self.main_win.findChild(cls, name)
            setattr(self, attr, w)
            self.widgets[attr] = w

    # -------------------------------------------------------------------------
    def _connect_signals(self, connections) -> None:
        for attr, signal, slot in connections:
            widget = self.widgets[attr]
            getattr(widget, signal).connect(slot)

    # -------------------------------------------------------------------------
    def _set_widgets_from_configuration(self) -> None:
        cfg = self.config_manager.get_configuration()
        for attr, widget in self.widgets.items():
            if attr not in cfg:
                continue
            v = cfg[attr]

            if hasattr(widget, "setChecked") and isinstance(v, bool):
                widget.setChecked(v)
            elif hasattr(widget, "setValue") and isinstance(v, (int, float)):
                widget.setValue(v)
            elif hasattr(widget, "setPlainText") and isinstance(v, str):
                widget.setPlainText(v)
            elif hasattr(widget, "setText") and isinstance(v, str):
                widget.setText(v)
            elif isinstance(widget, QComboBox):
                if isinstance(v, str):
                    idx = widget.findText(v)
                    if idx != -1:
                        widget.setCurrentIndex(idx)
                    elif widget.isEditable():
                        widget.setEditText(v)
                elif isinstance(v, int) and 0 <= v < widget.count():
                    widget.setCurrentIndex(v)

    # [SLOT]
    ###########################################################################
    # It's good practice to define methods that act as slots within the class
    # that manages the UI elements. These slots can then call methods on the
    # handler objects. Using @Slot decorator is optional but good practice
    # -------------------------------------------------------------------------
    @Slot()
    def stop_running_worker(self) -> None:
        if self.worker:
            self.worker.stop()
            self._send_message("Interrupt requested. Waiting for threads to stop...")

    # -------------------------------------------------------------------------
    @Slot()
    def _update_metrics(self) -> None:
        self.selected_metrics["dataset"] = [
            name for name, box in self.data_metrics if box and box.isChecked()
        ]
        self.selected_metrics["model"] = [
            name for name, box in self.model_metrics if box and box.isChecked()
        ]

    # -------------------------------------------------------------------------
    # [ACTIONS]
    # -------------------------------------------------------------------------
    @Slot()
    def save_configuration(self) -> None:
        dialog = SaveConfigDialog(self.main_win)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_name()
            name = "default_config" if not name else name
            self.config_manager.save_configuration_to_json(name)
            self._send_message(f"Configuration [{name}] has been saved")

    # -------------------------------------------------------------------------
    @Slot()
    def load_configuration(self) -> None:
        dialog = LoadConfigDialog(self.main_win)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_selected_config()
            if name:
                self.config_manager.load_configuration_from_json(name)
                self._set_widgets_from_configuration()
                self._send_message(f"Loaded configuration [{name}]")

    # -------------------------------------------------------------------------
    @Slot()
    def export_all_data(self) -> None:
        database.export_all_tables_as_csv()
        message = "All data from database has been exported"
        logger.info(message)
        self._send_message(message)

    # -------------------------------------------------------------------------
    @Slot()
    def delete_all_data(self) -> None:
        database.delete_all_data()
        message = "All data from database has been deleted"
        logger.info(message)
        self._send_message(message)

    # -------------------------------------------------------------------------
    # [GRAPHICS]
    # -------------------------------------------------------------------------
    @Slot()
    def _update_graphics_view(self) -> None:
        if not self.pixmaps:
            self.graphics["pixmap_item"].setPixmap(QPixmap())
            self.graphics["scene"].setSceneRect(0, 0, 0, 0)
            return

        idx = min(self.current_fig, len(self.pixmaps) - 1)
        raw = self.pixmaps[idx]

        qpixmap = QPixmap(raw) if isinstance(raw, str) else raw
        view = self.graphics["view"]
        pixmap_item = self.graphics["pixmap_item"]
        scene = self.graphics["scene"]
        view_size = view.viewport().size()
        scaled = qpixmap.scaled(
            view_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        pixmap_item.setPixmap(scaled)
        scene.setSceneRect(scaled.rect())

    # -------------------------------------------------------------------------
    @Slot()
    def show_previous_figure(self) -> None:
        if not self.pixmaps:
            return
        if self.current_fig > 0:
            self.current_fig -= 1
            self._update_graphics_view()

    # -------------------------------------------------------------------------
    @Slot()
    def show_next_figure(self) -> None:
        if not self.pixmaps:
            return
        if self.current_fig < len(self.pixmaps) - 1:
            self.current_fig += 1
            self._update_graphics_view()

    # -------------------------------------------------------------------------
    @Slot()
    def clear_figures(self) -> None:
        if not self.pixmaps:
            return
        self.pixmaps.clear()
        self.current_fig = 0
        self._update_graphics_view()
        self.graphics["pixmap_item"].setPixmap(QPixmap())
        self.graphics["scene"].setSceneRect(0, 0, 0, 0)
        self.graphics["view"].viewport().update()

    # -------------------------------------------------------------------------
    # [DATASET TAB]
    # -------------------------------------------------------------------------
    @Slot()
    def update_database_from_source(self) -> None:
        if self.worker:
            message = (
                "A task is currently running, wait for it to finish and then try again"
            )
            QMessageBox.warning(self.main_win, "Application is still busy", message)
            return

        # send message to status bar
        self._send_message("Updating database with source data...")

        # functions that are passed to the worker will be executed in a separate thread
        self.worker = ThreadWorker(database.update_database_from_source)

        # start worker and inject signals
        self._start_thread_worker(
            self.worker,
            on_finished=self.on_database_uploading_finished,
            on_error=self.on_error,
            on_interrupted=self.on_task_interrupted,
        )

    # -------------------------------------------------------------------------
    @Slot()
    def run_dataset_evaluation_pipeline(self) -> None:
        if self.worker:
            message = (
                "A task is currently running, wait for it to finish and then try again"
            )
            QMessageBox.warning(self.main_win, "Application is still busy", message)
            return

        if not self.selected_metrics["dataset"]:
            return

        self.configuration = self.config_manager.get_configuration()
        self.validation_handler = ValidationEvents(self.configuration)
        # send message to status bar
        self._send_message("Calculating image dataset evaluation metrics...")

        # functions that are passed to the worker will be executed in a separate thread
        self.worker = ThreadWorker(
            self.validation_handler.run_dataset_evaluation_pipeline,
            self.selected_metrics["dataset"],
        )

        # start worker and inject signals
        self._start_thread_worker(
            self.worker,
            on_finished=self.on_dataset_evaluation_finished,
            on_error=self.on_error,
            on_interrupted=self.on_task_interrupted,
        )

    # -------------------------------------------------------------------------
    # [TRAINING TAB]
    # -------------------------------------------------------------------------
    @Slot()
    def train_from_scratch(self) -> None:
        if self.worker:
            message = (
                "A task is currently running, wait for it to finish and then try again"
            )
            QMessageBox.warning(self.main_win, "Application is still busy", message)
            return

        self.configuration = self.config_manager.get_configuration()
        self.model_handler = ModelEvents(self.configuration)

        # send message to status bar
        self._send_message("Training FAIRS QNet  using a new model instance...")
        # functions that are passed to the worker will be executed in a separate thread
        self.worker = ProcessWorker(self.model_handler.run_training_pipeline)

        # start worker and inject signals
        self._start_process_worker(
            self.worker,
            on_finished=self.on_train_finished,
            on_error=self.on_error,
            on_interrupted=self.on_task_interrupted,
        )

    # -------------------------------------------------------------------------
    @Slot()
    def resume_training_from_checkpoint(self) -> None:
        if self.worker:
            message = (
                "A task is currently running, wait for it to finish and then try again"
            )
            QMessageBox.warning(self.main_win, "Application is still busy", message)
            return

        if not self.selected_checkpoint:
            return

        self.configuration = self.config_manager.get_configuration()
        self.model_handler = ModelEvents(self.configuration)

        # send message to status bar
        self._send_message(
            f"Resume training from checkpoint {self.selected_checkpoint}"
        )
        # functions that are passed to the worker will be executed in a separate thread
        self.worker = ProcessWorker(
            self.model_handler.resume_training_pipeline, self.selected_checkpoint
        )

        # start worker and inject signals
        self._start_process_worker(
            self.worker,
            on_finished=self.on_train_finished,
            on_error=self.on_error,
            on_interrupted=self.on_task_interrupted,
        )

    # -------------------------------------------------------------------------
    # [MODEL EVALUATION AND INFERENCE TAB]
    # -------------------------------------------------------------------------
    @Slot()
    def load_checkpoints(self) -> None:
        checkpoints = self.model_handler.get_available_checkpoints()
        self.checkpoints_list.clear()
        if checkpoints:
            self.checkpoints_list.addItems(checkpoints)
            self.selected_checkpoint = checkpoints[0]
            self.checkpoints_list.setCurrentText(checkpoints[0])
        else:
            self.selected_checkpoint = None
            logger.warning("No checkpoints available")

    # -------------------------------------------------------------------------
    @Slot()
    def select_checkpoint(self, name: str) -> None:
        self.selected_checkpoint = name if name else None

    # -------------------------------------------------------------------------
    @Slot()
    def run_model_evaluation_pipeline(self) -> None:
        if self.worker:
            message = (
                "A task is currently running, wait for it to finish and then try again"
            )
            QMessageBox.warning(self.main_win, "Application is still busy", message)
            return

        if not self.selected_metrics["model"] or not self.selected_checkpoint:
            return

        self.configuration = self.config_manager.get_configuration()
        self.validation_handler = ValidationEvents(self.configuration)

        # send message to status bar
        self._send_message(f"Evaluating {self.selected_checkpoint} performances... ")

        # functions that are passed to the worker will be executed in a separate thread
        self.worker = ProcessWorker(
            self.validation_handler.run_model_evaluation_pipeline,
            self.selected_metrics["model"],
            self.selected_checkpoint,
        )

        # start worker and inject signals
        self._start_process_worker(
            self.worker,
            on_finished=self.on_model_evaluation_finished,
            on_error=self.on_error,
            on_interrupted=self.on_task_interrupted,
        )

    # -------------------------------------------------------------------------
    @Slot()
    def get_checkpoints_summary(self) -> None:
        if self.worker:
            message = (
                "A task is currently running, wait for it to finish and then try again"
            )
            QMessageBox.warning(self.main_win, "Application is still busy", message)
            return

        self.configuration = self.config_manager.get_configuration()
        self.validation_handler = ValidationEvents(self.configuration)
        # send message to status bar
        self._send_message("Generating checkpoints summary...")

        # functions that are passed to the worker will be executed in a separate thread
        self.worker = ThreadWorker(self.validation_handler.get_checkpoints_summary)

        # start worker and inject signals
        self._start_thread_worker(
            self.worker,
            on_finished=self.on_model_evaluation_finished,
            on_error=self.on_error,
            on_interrupted=self.on_task_interrupted,
        )

    # -------------------------------------------------------------------------
    # [INFERENCE TAB]
    # -------------------------------------------------------------------------
    @Slot()
    def play_roulette(self) -> None:
        if self.worker:
            QMessageBox.warning(
                self.main_win,
                "Application is still busy",
                "A task is currently running, wait for it to finish and then try again",
            )
            return

        if not self.selected_checkpoint:
            return

        cfg = self.config_manager.get_configuration()
        dlg = RouletteDialog(self.main_win, cfg, self.selected_checkpoint)
        dlg.exec()
        return

    ###########################################################################
    # [POSITIVE OUTCOME HANDLERS]
    ###########################################################################
    def on_database_uploading_finished(self, source_data: pd.DataFrame) -> None:
        message = f"Database updated with source data ({len(source_data[0])}) records"
        self._send_message(message)
        QMessageBox.information(self.main_win, "Database successfully updated", message)
        self.worker = self.worker.cleanup() if self.worker else None

    # -------------------------------------------------------------------------
    def on_dataset_evaluation_finished(self, plots) -> None:
        self._send_message("Figures have been generated")
        self.worker = self.worker.cleanup() if self.worker else None

    # -------------------------------------------------------------------------
    def on_train_finished(self, session) -> None:
        self._send_message("Training session is over. Model has been saved")
        self.worker = self.worker.cleanup() if self.worker else None

    # -------------------------------------------------------------------------
    def on_model_evaluation_finished(self, plots) -> None:
        self._send_message(f"Model {self.selected_checkpoint} has been evaluated")
        self.worker = self.worker.cleanup() if self.worker else None

    # -------------------------------------------------------------------------
    def on_inference_finished(self, session) -> None:
        self._send_message("Inference call has been terminated")
        self.worker = self.worker.cleanup() if self.worker else None

    ###########################################################################
    # [NEGATIVE OUTCOME HANDLERS]
    ###########################################################################
    def on_error(self, err_tb : tuple[str, str]) -> None:
        exc, tb = err_tb
        logger.error(f"{exc}\n{tb}")
        message = "An error occurred during the operation. Check the logs for details."
        QMessageBox.critical(self.main_win, "Something went wrong!", message)
        self.progress_bar.setValue(0) if self.progress_bar else None
        self.worker = self.worker.cleanup() if self.worker else None

    ###########################################################################
    # [INTERRUPTION HANDLERS]
    ###########################################################################
    def on_task_interrupted(self) -> None:
        self.progress_bar.setValue(0) if self.progress_bar else None
        self._send_message("Current task has been interrupted by user")
        logger.warning("Current task has been interrupted by user")
        self.worker = self.worker.cleanup() if self.worker else None
