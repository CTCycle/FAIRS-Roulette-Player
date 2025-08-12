import os 
import multiprocessing as mp
import queue as stdq

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QLabel, QPushButton, 
                               QDialogButtonBox, QListWidget, QHBoxLayout, QMessageBox)

from FAIRS.app.interface.events import ModelEvents
from FAIRS.app.interface.workers import ProcessWorker
from FAIRS.app.constants import CONFIG_PATH
from FAIRS.app.logger import logger
         

###############################################################################
class SaveConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Configuration As")
        self.layout = QVBoxLayout(self)

        self.label = QLabel("Enter a name for your configuration:", self)
        self.layout.addWidget(self.label)

        self.name_edit = QLineEdit(self)
        self.layout.addWidget(self.name_edit)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def get_name(self):
        return self.name_edit.text().strip()       

###############################################################################   
class LoadConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Configuration")
        self.layout = QVBoxLayout(self)

        self.label = QLabel("Select a configuration:", self)
        self.layout.addWidget(self.label)

        self.config_list = QListWidget(self)
        self.layout.addWidget(self.config_list)

        # Populate the list with available .json files
        configs = [f for f in os.listdir(CONFIG_PATH) if f.endswith('.json')]
        self.config_list.addItems(configs)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def get_selected_config(self):
        selected = self.config_list.currentItem()
        return selected.text() if selected else None
    
###############################################################################  
class RouletteDialog(QDialog):
    """
    Modal dialog that controls real-time roulette inference running in a child process.
    Communicates via mp.Queues with ModelEvents.run_inference_pipeline.

    Events from child:
      {"kind":"prediction","action":int,"description":str}
      {"kind":"updated","value":int}
      {"kind":"error","detail":str}
      {"kind":"closed"}
    """
    def __init__(self, parent, configuration, checkpoint_name):
        super().__init__(parent)
        self.setWindowTitle("Roulette – Live")
        self.setModal(True)
        self.configuration = configuration
        self.checkpoint = checkpoint_name

        # --- UI ---
        layout = QVBoxLayout(self)
        self.pred_label = QLabel("Predicted: —")
        self.pred_label.setWordWrap(True)
        layout.addWidget(self.pred_label)

        next_row = QHBoxLayout()
        self.btn_next = QPushButton("Next extraction")
        self.btn_next.clicked.connect(self.get_next_prediction)
        next_row.addWidget(self.btn_next)
        layout.addLayout(next_row)

        update_row = QHBoxLayout()
        self.true_edit = QLineEdit()
        self.true_edit.setPlaceholderText("Update with current extraction (0–36)")
        self.true_edit.setMaxLength(2)  # "36" max
        self.true_edit.setClearButtonEnabled(True)
        self.btn_update = QPushButton("Update")
        self.btn_update.clicked.connect(self.on_update_clicked)
        update_row.addWidget(self.true_edit)
        update_row.addWidget(self.btn_update)
        layout.addLayout(update_row)

        close_row = QHBoxLayout()
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        close_row.addStretch(1)
        close_row.addWidget(self.btn_close)
        layout.addLayout(close_row)
        self.setMinimumWidth(420)

        # --- IPC: spawn-safe queues + process worker
        ctx = mp.get_context("spawn")
        self.cmd_q: mp.Queue = ctx.Queue()
        self.out_q: mp.Queue = ctx.Queue()

        self.worker = ProcessWorker(
            ModelEvents.run_inference_pipeline,
            self.configuration,
            self.checkpoint,
            self.cmd_q,
            self.out_q
        )
        self._start_process_worker(
            self.worker,
            on_finished=self._on_proc_finished,
            on_error=self._on_proc_error,
            on_interrupted=self._on_proc_interrupted
        )

        # Poll child -> dialog queue
        self.out_timer = QTimer(self)
        self.out_timer.setInterval(60)
        self.out_timer.timeout.connect(self._drain_out_queue)
        self.out_timer.start()

        # Start in idle-ready state
        self._busy(False)

    # -------------------- process worker plumbing ----------------------------
    def _start_process_worker(self, worker: ProcessWorker, on_finished, on_error, on_interrupted):
        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        worker.signals.interrupted.connect(on_interrupted)

        self.process_worker_timer = QTimer(self)
        self.process_worker_timer.setInterval(100)
        self.process_worker_timer.timeout.connect(worker.poll)
        worker._timer = self.process_worker_timer
        self.process_worker_timer.start()
        worker.start()

    # -------------------- UI actions ----------------------------------------
    @Slot()
    def get_next_prediction(self):
        try:
            self._busy(True)
            self.cmd_q.put({"kind": "next"})
        except Exception as e:
            QMessageBox.critical(self, "Request error", f"Could not send next: {e!r}")
            self._busy(False)

    @Slot()
    def on_update_clicked(self):
        txt = self.true_edit.text().strip()
        # Validate strictly: integer in [0, 36]
        try:
            if txt == "":
                raise ValueError("Value is empty")
            val = int(txt, 10)
            if not (0 <= val <= 36):
                raise ValueError("Value must be between 0 and 36")
        except Exception as e:
            QMessageBox.warning(self, "Invalid value", f"Please enter an integer in [0, 36].\n\nDetail: {e}")
            return

        try:
            self._busy(True)
            self.cmd_q.put({"kind": "update", "value": val})
        except Exception as e:
            QMessageBox.critical(self, "Request error", f"Could not send update: {e!r}")
            self._busy(False)

    # -------------------- queue draining ------------------------------------
    def _drain_out_queue(self):
        # Non-blocking drain of out_q
        drained = False
        while True:
            try:
                msg = self.out_q.get_nowait()
            except stdq.Empty:
                break
            except Exception as e:
                logger.error(f"Dialog out_q error: {e!r}")
                break

            drained = True
            kind = msg.get("kind")

            if kind == "prediction":
                action = msg.get("action")
                desc = msg.get("description", str(action))
                self.pred_label.setText(f"Predicted: {desc} (id={action})")
                self._busy(False)

            elif kind == "updated":
                v = msg.get("value")
                self.true_edit.clear()
                self.pred_label.setText(f"Updated with true extraction: {v}")
                self._busy(False)

            elif kind == "error":
                detail = msg.get("detail", "Unknown error")
                logger.error(f"[child error] {detail}")
                QMessageBox.critical(self, "Worker error", detail)
                self._busy(False)

            elif kind == "closed":
                # Child says it's done; stop timers and close if still open
                self._teardown_timers()
                if self.isVisible():
                    self.accept()

        # Optional: could update a status if nothing arrived recently
        if not drained:
            return

    # -------------------- helpers / lifecycle --------------------------------
    def _busy(self, is_busy: bool):
        # Disable only the action buttons; allow dialog close
        self.btn_next.setEnabled(not is_busy)
        self.btn_update.setEnabled(not is_busy)
        self.btn_close.setEnabled(True)

    def _teardown_timers(self):
        if hasattr(self, "out_timer") and self.out_timer.isActive():
            self.out_timer.stop()
        if hasattr(self, "process_worker_timer") and self.process_worker_timer.isActive():
            self.process_worker_timer.stop()

    def _shutdown_child(self):
        try:
            # Ask child loop to exit gracefully
            self.cmd_q.put({"kind": "shutdown"})
        except Exception:
            pass
        finally:
            try:
                # Ensure process is torn down even if child is stuck
                self.worker.cleanup()
            except Exception:
                pass

    def closeEvent(self, event):
        # On any form of close, request shutdown and clean timers
        self._teardown_timers()
        self._shutdown_child()
        super().closeEvent(event)

    # -------------------- process callbacks ----------------------------------
    def _on_proc_finished(self, _):
        # Child function returned (should normally not happen until shutdown)
        self._teardown_timers()
        self._busy(False)

    def _on_proc_error(self, err_tb):
        exc, tb = err_tb
        logger.error(f"Child process error: {exc}\n{tb}")
        self._teardown_timers()
        self._busy(False)
        QMessageBox.critical(self, "Process error", "An error occurred. Check logs for details.")

    def _on_proc_interrupted(self):
        self._teardown_timers()
        self._busy(False)