from __future__ import annotations

import multiprocessing as mp
import os
import queue as stdq
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from FAIRS.app.client.events import ModelEvents
from FAIRS.app.client.workers import ProcessWorker, ThreadWorker
from FAIRS.app.utils.constants import CONFIG_PATH
from FAIRS.app.utils.logger import logger


###############################################################################
class SaveConfigDialog(QDialog):
    def __init__(self, parent: QMainWindow | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save Configuration As")
        self.dialog_layout = QVBoxLayout(self)

        self.label = QLabel("Enter a name for your configuration:", self)
        self.dialog_layout.addWidget(self.label)

        self.name_edit = QLineEdit(self)
        self.dialog_layout.addWidget(self.name_edit)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.dialog_layout.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def get_name(self) -> str:
        return self.name_edit.text().strip()


###############################################################################
class LoadConfigDialog(QDialog):
    def __init__(self, parent: QMainWindow | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Load Configuration")
        self.dialog_layout = QVBoxLayout(self)

        self.label = QLabel("Select a configuration:", self)
        self.dialog_layout.addWidget(self.label)

        self.config_list = QListWidget(self)
        self.dialog_layout.addWidget(self.config_list)

        # Populate the list with available .json files
        configs: list[str] = [f for f in os.listdir(CONFIG_PATH) if f.endswith(".json")]
        self.config_list.addItems(configs)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.dialog_layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def get_selected_config(self) -> str | None:
        selected = self.config_list.currentItem()
        return selected.text() if selected else None


###############################################################################
class RouletteDialog(QDialog):
    """
    Modal dialog that controls real-time roulette inference running in a child process.
    Child process target: ModelEvents.run_inference_pipeline

    Child -> Dialog events:
      {"kind":"ready"}
      {"kind":"prediction","action":int,"description":str}
      {"kind":"updated","value":int}
      {"kind":"error","detail":str}
      {"kind":"closed"}

    """

    def __init__(
        self,
        parent: QMainWindow | None,
        configuration: dict[str, Any],
        checkpoint_name: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Roulette Live")
        self.setModal(True)
        self.configuration = configuration
        self.checkpoint = checkpoint_name

        # Runtime state
        self.started = False
        self.worker: ThreadWorker | ProcessWorker | None = None
        self.cmd_q = None
        self.out_q = None
        self.process_worker_timer = None
        self.out_timer = None

        # State flags used to compute UI enabledness
        self.ready = False
        self.loading = False
        self.busy = False

        # --- UI ---
        layout = QVBoxLayout(self)

        # TOP row: Start + Close
        top_row = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.start_player)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        top_row.addWidget(self.btn_start)
        top_row.addStretch(1)
        top_row.addWidget(self.btn_close)
        layout.addLayout(top_row)

        # Prediction + Next extraction row
        pred_row = QHBoxLayout()
        self.pred_label = QLabel("Click Start to load model & data…")
        self.pred_label.setWordWrap(True)
        pred_row.addWidget(self.pred_label, stretch=1)
        self.btn_next = QPushButton("Next extraction")
        self.btn_next.clicked.connect(self.get_next_prediction)
        pred_row.addWidget(self.btn_next)
        layout.addLayout(pred_row)

        # UPDATE row: Text box + Update
        update_row = QHBoxLayout()
        self.true_edit = QLineEdit()
        self.true_edit.setPlaceholderText("Update with current extraction (0–36)")
        self.true_edit.setMaxLength(2)
        self.true_edit.setClearButtonEnabled(True)
        self.btn_update = QPushButton("Update")
        self.btn_update.clicked.connect(self.on_update_clicked)
        update_row.addWidget(self.true_edit)
        update_row.addWidget(self.btn_update)
        layout.addLayout(update_row)

        self.setMinimumWidth(420)

        # Initial state: only Start/Close enabled
        self.set_controls_enabled(ready=False, loading=False)

    # -------------------- start flow -----------------------------------------
    @Slot()
    def start_player(self) -> None:
        if self.started:
            return
        self.started = True
        self.set_controls_enabled(ready=False, loading=True)
        self.pred_label.setText("Loading model & data…")

        ctx = mp.get_context("spawn")
        self.cmd_q = ctx.Queue()
        self.out_q = ctx.Queue()

        self.worker = ProcessWorker(
            ModelEvents.run_inference_pipeline,
            self.configuration,
            self.checkpoint,
            self.cmd_q,
            self.out_q,
        )

        self.start_process_worker(
            self.worker,
            on_finished=self.on_proc_finished,  # type: ignore
            on_error=self.on_proc_error,  # type: ignore
            on_interrupted=self.on_proc_interrupted,
        )

        # Start polling child->dialog queue only after process starts
        self.out_timer = QTimer(self)
        self.out_timer.setInterval(100)
        self.out_timer.timeout.connect(self.drain_out_queue)
        self.out_timer.start()

    # -------------------------------------------------------------------------
    def start_process_worker(
        self,
        worker: ProcessWorker,
        on_finished: Callable[[], None],
        on_error: Callable[[], None],
        on_interrupted: Callable[[], None],
    ) -> None:
        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        worker.signals.interrupted.connect(on_interrupted)

        self.process_worker_timer = QTimer(self)
        self.process_worker_timer.setInterval(100)
        self.process_worker_timer.timeout.connect(worker.poll)
        worker.timer = self.process_worker_timer
        self.process_worker_timer.start()
        worker.start()

    # -------------------- UI actions ----------------------------------------
    @Slot()
    def get_next_prediction(self) -> None:
        if not self.ready:
            return
        self.busy_toggle(True)
        try:
            if self.cmd_q:
                self.cmd_q.put({"kind": "next"})
        except Exception as e:
            QMessageBox.critical(
                self, "Request error", f"Could not send request: {e!r}"
            )
            self.busy_toggle(False)

    @Slot()
    def on_update_clicked(self) -> None:
        txt = self.true_edit.text().strip()
        try:
            if txt == "":
                raise ValueError("Value is empty")
            val = int(txt, 10)
            if not (0 <= val <= 36):
                raise ValueError("Value must be between 0 and 36")
        except Exception as e:
            QMessageBox.warning(
                self,
                "Invalid value",
                f"Please enter an integer in [0, 36].\n\nDetail: {e}",
            )
            return

        try:
            self.busy_toggle(True)
            if self.cmd_q:
                self.cmd_q.put({"kind": "update", "value": val})
        except Exception as e:
            QMessageBox.critical(self, "Request error", f"Could not send update: {e!r}")
            self.busy_toggle(False)

    # -------------------- queue draining ------------------------------------
    def drain_out_queue(self) -> None:
        drained_any = False
        while True:
            try:
                if not self.out_q:
                    break
                msg = self.out_q.get_nowait()
            except stdq.Empty:
                break
            except Exception as e:
                logger.error(f"Dialog out_q error: {e!r}")
                break

            drained_any = True
            kind = msg.get("kind")

            if kind == "ready":
                # Child finished loading and entered the while-loop
                self.pred_label.setText("Ready for prediction")
                self.set_controls_enabled(ready=True, loading=False)

            elif kind == "prediction":
                action = msg.get("action")
                desc = msg.get("description", str(action))
                self.pred_label.setText(f"Predicted: {desc} (id={action})")
                self.busy_toggle(False)

            elif kind == "updated":
                v = msg.get("value")
                self.true_edit.clear()
                self.pred_label.setText(f"Updated with true extraction: {v}")
                self.busy_toggle(False)

            elif kind == "error":
                detail = msg.get("detail", "Unknown error")
                logger.error(f"[child error] {detail}")
                QMessageBox.critical(self, "Worker error", detail)
                self.busy_toggle(False)

            elif kind == "closed":
                self.teardown_timers()
                if self.isVisible():
                    self.accept()

        if not drained_any:
            return

    # -------------------- helpers / lifecycle --------------------------------
    def apply_enabled(self) -> None:
        """Compute enabled flags from self.ready/loading/busy."""
        # Start is only available before loading and before ready
        self.btn_start.setEnabled((not self.loading) and (not self.ready))
        # Action buttons require ready and not busy
        actions_enabled = self.ready and (not self.busy)
        self.btn_next.setEnabled(actions_enabled)
        self.btn_update.setEnabled(actions_enabled)
        # Close stays enabled always
        self.btn_close.setEnabled(True)

    def set_controls_enabled(self, *, ready: bool, loading: bool) -> None:
        self.ready = ready
        self.loading = loading
        self.apply_enabled()

    def busy_toggle(self, is_busy: bool) -> None:
        self.busy = is_busy
        self.apply_enabled()

    def teardown_timers(self) -> None:
        if self.out_timer and self.out_timer.isActive():
            self.out_timer.stop()
        if self.process_worker_timer and self.process_worker_timer.isActive():
            self.process_worker_timer.stop()

    def shutdown_child(self) -> None:
        if not self.started:
            return
        try:
            if self.cmd_q:
                self.cmd_q.put({"kind": "shutdown"})
        except Exception:
            pass
        finally:
            try:
                if self.worker:
                    self.worker.cleanup() if self.worker else None
            except Exception:
                pass

    def closeEvent(self, event) -> None:
        self.teardown_timers()
        self.shutdown_child()
        super().closeEvent(event)

    # -------------------- process callbacks ----------------------------------
    def on_proc_finished(self, _) -> None:
        self.teardown_timers()
        self.busy_toggle(False)

    def on_proc_error(self, err_tb: tuple[str, str]) -> None:
        exc, tb = err_tb
        logger.error(f"Child process error: {exc}\n{tb}")
        self.teardown_timers()
        self.busy_toggle(False)
        QMessageBox.critical(
            self, "Process error", "An error occurred. Check logs for details."
        )

    def on_proc_interrupted(self) -> None:
        self.teardown_timers()
        self.busy_toggle(False)
