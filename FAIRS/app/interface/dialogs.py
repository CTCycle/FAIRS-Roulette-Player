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
    def __init__(self, parent, configuration, checkpoint_name):
        super().__init__(parent)
        self.setWindowTitle("Roulette – Live")
        self.setModal(True)
        self.configuration = configuration
        self.checkpoint = checkpoint_name

        # Runtime state
        self.started = False
        self.worker = None
        self.cmd_q = None
        self.out_q = None
        self.process_worker_timer = None
        self.out_timer = None

        # State flags used to compute UI enabledness
        self._ready = False
        self._loading = False
        self._busy = False

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
        self._set_controls_enabled(ready=False, loading=False)

    # -------------------- start flow -----------------------------------------
    @Slot()
    def start_player(self):
        if self.started:
            return
        self.started = True
        self._set_controls_enabled(ready=False, loading=True)
        self.pred_label.setText("Loading model & data…")

        ctx = mp.get_context("spawn")
        self.cmd_q = ctx.Queue()
        self.out_q = ctx.Queue()

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

        # Start polling child->dialog queue only after process starts
        self.out_timer = QTimer(self)
        self.out_timer.setInterval(100)
        self.out_timer.timeout.connect(self._drain_out_queue)
        self.out_timer.start()

    #--------------------------------------------------------------------------
    def _start_process_worker(self, worker, on_finished, on_error, on_interrupted):
        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        worker.signals.interrupted.connect(on_interrupted)

        self.process_worker_timer = QTimer(self)
        self.process_worker_timer.setInterval(100)
        self.process_worker_timer.timeout.connect(worker.poll)
        worker._timer = self.process_worker_timer  # if your ProcessWorker expects it
        self.process_worker_timer.start()
        worker.start()

    # -------------------- UI actions ----------------------------------------
    @Slot()
    def get_next_prediction(self):
        if not self._ready:
            return
        self._busy_toggle(True)
        try:
            self.cmd_q.put({"kind": "next"})
        except Exception as e:
            QMessageBox.critical(self, "Request error", f"Could not send request: {e!r}")
            self._busy_toggle(False)

    @Slot()
    def on_update_clicked(self):
        txt = self.true_edit.text().strip()
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
            self._busy_toggle(True)
            self.cmd_q.put({"kind": "update", "value": val})
        except Exception as e:
            QMessageBox.critical(self, "Request error", f"Could not send update: {e!r}")
            self._busy_toggle(False)

    # -------------------- queue draining ------------------------------------
    def _drain_out_queue(self):
        drained_any = False
        while True:
            try:
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
                self._set_controls_enabled(ready=True, loading=False)

            elif kind == "prediction":
                action = msg.get("action")
                desc = msg.get("description", str(action))
                self.pred_label.setText(f"Predicted: {desc} (id={action})")
                self._busy_toggle(False)

            elif kind == "updated":
                v = msg.get("value")
                self.true_edit.clear()
                self.pred_label.setText(f"Updated with true extraction: {v}")
                self._busy_toggle(False)

            elif kind == "error":
                detail = msg.get("detail", "Unknown error")
                logger.error(f"[child error] {detail}")
                QMessageBox.critical(self, "Worker error", detail)
                self._busy_toggle(False)

            elif kind == "closed":
                self._teardown_timers()
                if self.isVisible():
                    self.accept()

        if not drained_any:
            return

    # -------------------- helpers / lifecycle --------------------------------
    def _apply_enabled(self):
        """Compute enabled flags from self._ready/_loading/_busy."""
        # Start is only available before loading and before ready
        self.btn_start.setEnabled((not self._loading) and (not self._ready))
        # Action buttons require ready and not busy
        actions_enabled = self._ready and (not self._busy)
        self.btn_next.setEnabled(actions_enabled)
        self.btn_update.setEnabled(actions_enabled)
        # Close stays enabled always
        self.btn_close.setEnabled(True)

    def _set_controls_enabled(self, *, ready: bool, loading: bool):
        self._ready = ready
        self._loading = loading
        self._apply_enabled()

    def _busy_toggle(self, is_busy: bool):
        self._busy = is_busy
        self._apply_enabled()

    def _teardown_timers(self):
        if self.out_timer and self.out_timer.isActive():
            self.out_timer.stop()
        if self.process_worker_timer and self.process_worker_timer.isActive():
            self.process_worker_timer.stop()

    def _shutdown_child(self):
        if not self.started:
            return
        try:
            self.cmd_q.put({"kind": "shutdown"})
        except Exception:
            pass
        finally:
            try:
                self.worker.cleanup()
            except Exception:
                pass

    def closeEvent(self, event):
        self._teardown_timers()
        self._shutdown_child()
        super().closeEvent(event)

    # -------------------- process callbacks ----------------------------------
    def _on_proc_finished(self, _):
        self._teardown_timers()
        self._busy_toggle(False)

    def _on_proc_error(self, err_tb):
        exc, tb = err_tb
        logger.error(f"Child process error: {exc}\n{tb}")
        self._teardown_timers()
        self._busy_toggle(False)
        QMessageBox.critical(self, "Process error", "An error occurred. Check logs for details.")

    def _on_proc_interrupted(self):
        self._teardown_timers()
        self._busy_toggle(False)