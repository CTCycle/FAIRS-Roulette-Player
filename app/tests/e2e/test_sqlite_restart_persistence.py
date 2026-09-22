"""Process-restart persistence coverage using an isolated SQLite data root."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterator

import httpx


APP_ROOT = Path(__file__).resolve().parents[2]
_ISOLATED_UVICORN_RUNNER = """
import os
import sys
from threading import Thread
import uvicorn
import server.bootstrap as bootstrap
from server.common import path as shared_paths

original_bootstrap = bootstrap.bootstrap_runtime
original_configure_runtime_paths = shared_paths.configure_runtime_paths
data_root = os.environ["FAIRS_VAL05_DATA_ROOT"]

def configure_isolated_data_root(_data_dir=None):
    original_configure_runtime_paths(data_root)

def isolated_bootstrap():
    shared_paths.configure_runtime_paths = configure_isolated_data_root
    try:
        original_bootstrap()
    finally:
        shared_paths.configure_runtime_paths = original_configure_runtime_paths
    os.environ["FAIRS_DATA_DIR"] = data_root

bootstrap.bootstrap_runtime = isolated_bootstrap
import server.app as application
application.bootstrap_runtime = isolated_bootstrap

server = uvicorn.Server(
    uvicorn.Config(
        application.app,
        host="127.0.0.1",
        port=int(os.environ["FAIRS_VAL05_PORT"]),
        workers=1,
        log_level="info",
    )
)

def request_shutdown():
    sys.stdin.buffer.readline()
    server.should_exit = True

Thread(target=request_shutdown, daemon=True).start()
server.run()
print("FAIRS_RESTART_TEST_SERVER_STOPPED", flush=True)
"""


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _log_tail(log_path: Path) -> str:
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8", errors="replace")[-4000:]


def _wait_until_ready(
    process: subprocess.Popen[str], base_url: str, log_path: Path
) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Isolated backend exited with {process.returncode}:\n{_log_tail(log_path)}"
            )
        try:
            response = httpx.get(
                f"{base_url}/api/health", timeout=2, trust_env=False
            )
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"Isolated backend did not become healthy:\n{_log_tail(log_path)}")


@contextmanager
def _running_backend(
    data_root: Path, log_path: Path
) -> Iterator[httpx.Client]:
    port = _available_port()
    child_environment = os.environ.copy()
    child_environment["FAIRS_VAL05_DATA_ROOT"] = str(data_root)
    child_environment["FAIRS_VAL05_PORT"] = str(port)

    with log_path.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [sys.executable, "-c", _ISOLATED_UVICORN_RUNNER],
            cwd=APP_ROOT,
            env=child_environment,
            stdin=subprocess.PIPE,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            _wait_until_ready(process, base_url, log_path)
            with httpx.Client(
                base_url=f"{base_url}/api", timeout=30, trust_env=False
            ) as client:
                yield client
        finally:
            if process.poll() is None:
                try:
                    assert process.stdin is not None
                    process.stdin.write("stop\n")
                    process.stdin.flush()
                    process.stdin.close()
                    process.wait(timeout=30)
                    if process.returncode != 0:
                        raise RuntimeError(
                            f"Isolated backend shutdown returned {process.returncode}:\n"
                            f"{_log_tail(log_path)}"
                        )
                    if "FAIRS_RESTART_TEST_SERVER_STOPPED" not in _log_tail(log_path):
                        raise RuntimeError(
                            "Isolated backend did not confirm graceful shutdown:\n"
                            f"{_log_tail(log_path)}"
                        )
                except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)


def _training_summary(client: httpx.Client) -> list[dict[str, object]]:
    response = client.get("/datasets/training/summary")
    assert response.status_code == 200, response.text
    return response.json()["datasets"]


def _assert_alembic_head(database_path: Path) -> None:
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
    assert revision == ("0002_rename_relative_preference",)


def test_uploaded_dataset_survives_backend_restart_and_stays_deleted(
    tmp_path: Path,
) -> None:
    """Upload, stop, restart, delete, and restart against one SQLite file."""
    data_root = tmp_path / "fairs-data"
    database_path = data_root / "database.db"
    log_path = tmp_path / "isolated-backend.log"
    dataset_name = "val05_restart_persistence"
    csv_content = b"draw_index,observed_outcome\n0,0\n1,17\n2,36\n3,9\n"

    assert not data_root.exists()

    with _running_backend(data_root, log_path) as client:
        assert _training_summary(client) == []
        upload = client.post(
            "/data/upload?dataset_kind=training&csv_separator=%2C",
            files={
                "file": (
                    f"{dataset_name}.csv",
                    csv_content,
                    "text/csv",
                )
            },
        )
        assert upload.status_code == 200, upload.text
        payload = upload.json()
        dataset_id = payload["dataset_id"]
        assert payload["dataset_name"] == dataset_name
        assert payload["rows_imported"] == 4
        first_summary = _training_summary(client)
        assert len(first_summary) == 1
        assert first_summary[0]["dataset_id"] == dataset_id
        assert first_summary[0]["dataset_name"] == dataset_name
        assert first_summary[0]["dataset_kind"] == "training"
        assert first_summary[0]["row_count"] == 4

    _assert_alembic_head(database_path)

    with _running_backend(data_root, log_path) as client:
        restarted_summary = _training_summary(client)
        assert restarted_summary == first_summary
        assert restarted_summary[0]["dataset_id"] == dataset_id
        assert restarted_summary[0]["row_count"] == 4
        delete = client.delete(f"/datasets/training/{dataset_id}")
        assert delete.status_code == 200, delete.text
        assert delete.json()["dataset_id"] == dataset_id
        assert _training_summary(client) == []

    with _running_backend(data_root, log_path) as client:
        assert _training_summary(client) == []

    _assert_alembic_head(database_path)
