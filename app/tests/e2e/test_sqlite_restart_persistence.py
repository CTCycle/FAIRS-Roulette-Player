"""Process-restart persistence coverage using an isolated SQLite data root."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator

import httpx
import pytest
from playwright.sync_api import Page, expect


APP_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = APP_ROOT.parent
_ISOLATED_UVICORN_RUNNER = """
import os
import sys
from threading import Thread
import uvicorn
import server.bootstrap as bootstrap
from server.common import path as shared_paths

original_bootstrap = bootstrap.bootstrap_runtime
original_configure_runtime_paths = shared_paths.configure_runtime_paths
data_root = os.environ["FAIRS_RESTART_TEST_DATA_ROOT"]

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
        port=int(os.environ["FAIRS_RESTART_TEST_PORT"]),
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


@pytest.fixture
def isolated_app_data_parent(
    request: pytest.FixtureRequest, isolated_app_data_temp_root: Path
) -> Path:
    """Keep app data outside cache and defer cleanup until subprocesses have exited."""
    test_name = re.sub(r"[^A-Za-z0-9_.-]", "_", request.node.name)
    data_parent = isolated_app_data_temp_root / test_name
    data_parent.mkdir()
    return data_parent


@pytest.fixture(scope="session")
def isolated_app_data_temp_root() -> Iterator[Path]:
    """Give restart subprocesses a session-long data parent outside pytest's cache."""
    with tempfile.TemporaryDirectory(prefix="fairs-restart-data-") as temp_dir:
        yield Path(temp_dir)


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
    data_root: Path, log_path: Path, *, port: int | None = None
) -> Iterator[httpx.Client]:
    port = port or _available_port()
    child_environment = os.environ.copy()
    child_environment["FAIRS_RESTART_TEST_DATA_ROOT"] = str(data_root)
    child_environment["FAIRS_RESTART_TEST_PORT"] = str(port)
    child_environment["FASTAPI_HOST"] = "127.0.0.1"
    child_environment["FASTAPI_PORT"] = str(port)

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


@contextmanager
def _running_frontend(
    backend_port: int, ui_port: int, log_path: Path
) -> Iterator[str]:
    node_binary = PROJECT_ROOT / "runtimes" / "nodejs" / "node.exe"
    vite_entry = APP_ROOT / "client" / "node_modules" / "vite" / "bin" / "vite.js"
    if not node_binary.is_file() or not vite_entry.is_file():
        raise FileNotFoundError(
            "The managed Node runtime and installed Vite package are required "
            "for the isolated browser restart regression."
        )

    child_environment = os.environ.copy()
    child_environment.update(
        {
            "FASTAPI_HOST": "127.0.0.1",
            "FASTAPI_PORT": str(backend_port),
            "UI_HOST": "127.0.0.1",
            "UI_PORT": str(ui_port),
        }
    )
    base_url = f"http://127.0.0.1:{ui_port}"
    with log_path.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [
                str(node_binary),
                str(vite_entry),
                "--host",
                "127.0.0.1",
                "--port",
                str(ui_port),
                "--strictPort",
            ],
            cwd=APP_ROOT / "client",
            env=child_environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(
                        "Isolated frontend exited with "
                        f"{process.returncode}:\n{_log_tail(log_path)}"
                    )
                try:
                    response = httpx.get(base_url, timeout=2, trust_env=False)
                    if response.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.25)
            else:
                raise TimeoutError(
                    f"Isolated frontend did not become ready:\n{_log_tail(log_path)}"
                )
            yield base_url
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


def _copy_inference_restart_fixture(data_root: Path) -> Path:
    source_resources = APP_ROOT / "resources"
    database_path = data_root / "database.db"
    data_root.mkdir(parents=True)

    with sqlite3.connect(
        f"{(source_resources / 'database.db').resolve().as_uri()}?mode=ro",
        uri=True,
    ) as source, sqlite3.connect(database_path) as target:
        source.backup(target)

    shutil.copy2(source_resources / "runtime-settings.json", data_root)
    checkpoint_source = (
        source_resources / "checkpoints" / "val00_lineage_20260921"
    )
    if not checkpoint_source.is_dir():
        raise FileNotFoundError(f"Required VAL-00 checkpoint is missing: {checkpoint_source}")
    shutil.copytree(
        checkpoint_source,
        data_root / "checkpoints" / checkpoint_source.name,
    )
    return database_path


def _persisted_inference_session(
    database_path: Path, session_id: str
) -> tuple[tuple[object, ...], list[tuple[object, ...]]]:
    with sqlite3.connect(
        f"{database_path.resolve().as_uri()}?mode=ro", uri=True
    ) as database:
        session = database.execute(
            """
            SELECT dataset_id, checkpoint_name, initial_capital, ended_at
            FROM inference_sessions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        steps = database.execute(
            """
            SELECT step_number, bet_amount, predicted_action,
                   predicted_relative_preference, observed_outcome_id,
                   reward, capital_after
            FROM inference_session_steps
            WHERE session_id = ?
            ORDER BY step_number
            """,
            (session_id,),
        ).fetchall()
    assert session is not None, f"Inference session {session_id} was not persisted"
    return session, steps


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
    tmp_path: Path, isolated_app_data_parent: Path
) -> None:
    """Upload, stop, restart, delete, and restart against one SQLite file."""
    data_root = isolated_app_data_parent / "fairs-data"
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


def test_inference_session_recovers_live_and_expires_after_backend_restart(
    tmp_path: Path, page: Page, isolated_app_data_parent: Path
) -> None:
    """A browser restores a live session, then clears it after backend restart."""
    data_root = isolated_app_data_parent / "fairs-data"
    database_path = _copy_inference_restart_fixture(data_root)
    backend_port = _available_port()
    ui_port = _available_port()
    while ui_port == backend_port:
        ui_port = _available_port()
    backend_log = tmp_path / "isolated-inference-backend.log"
    frontend_log = tmp_path / "isolated-inference-frontend.log"
    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []
    failed_responses: list[str] = []
    expected_expired_session_url: str | None = None

    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda message: console_errors.append(message.text)
        if message.type == "error"
        else None,
    )
    page.on(
        "requestfailed",
        lambda request: failed_requests.append(
            f"{request.method} {request.url}: {request.failure}"
        ),
    )
    page.on(
        "response",
        lambda response: failed_responses.append(
            f"{response.status} {response.url}"
        )
        if response.status >= 400
        else None,
    )

    with _running_frontend(backend_port, ui_port, frontend_log) as frontend_url:
        with _running_backend(data_root, backend_log, port=backend_port) as client:
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{frontend_url}/inference", wait_until="domcontentloaded")
            page.locator(
                "#inference-checkpoint option[value='val00_lineage_20260921']"
            ).wait_for(state="attached")
            page.locator("#inference-dataset option[value='5']").wait_for(
                state="attached"
            )
            page.locator("#inference-checkpoint").select_option(
                "val00_lineage_20260921"
            )
            page.locator("#inference-dataset").select_option("5")
            page.locator("#inference-initial-capital").fill("1000")
            page.locator("#inference-bet-amount").fill("10")

            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith("/api/inference/sessions/start"),
                timeout=90_000,
            ) as start_info:
                page.get_by_role("button", name="Play", exact=True).click()
            start_response = start_info.value
            assert start_response.status == 200, start_response.text()
            session_id = str(start_response.json()["session_id"])

            rows = page.locator("table").get_by_role("row")
            expect(rows).to_have_count(2)
            first_row = rows.nth(1)
            prediction_text = first_row.get_by_role("cell").nth(1).inner_text()
            prediction_match = re.search(r"Bet on number (\d+)", prediction_text)
            assert prediction_match is not None, prediction_text
            predicted_number = int(prediction_match.group(1))
            observed_outcome = (predicted_number + 1) % 37
            page.get_by_label("Observed value for step 1").fill(
                str(observed_outcome)
            )
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith(
                    f"/api/inference/sessions/{session_id}/step"
                )
            ) as step_info:
                first_row.get_by_role("button", name="Confirm observed").click()
            assert step_info.value.status == 200, step_info.value.text()
            first_row.get_by_role("button", name="Next prediction").click()
            expect(rows).to_have_count(3)

            snapshot_response = client.get(f"/inference/sessions/{session_id}")
            assert snapshot_response.status_code == 200, snapshot_response.text
            original_snapshot = snapshot_response.json()
            assert original_snapshot["step_count"] == 1
            assert original_snapshot["prediction_pending"] is True
            assert [step["observed_outcome_id"] for step in original_snapshot["steps"]] == [
                observed_outcome,
                None,
            ]

            persisted = page.evaluate(
                "JSON.parse(window.localStorage.getItem('fairs.roulette.inference-session.v1'))"
            )
            assert persisted["config"]["sessionId"] == session_id

            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()
            expect(rows).to_have_count(3)
            expect(page.get_by_label("Observed value for step 1")).to_have_value(
                str(observed_outcome)
            )
            restored = client.get(f"/inference/sessions/{session_id}")
            assert restored.status_code == 200, restored.text
            assert restored.json() == original_snapshot

        with _running_backend(data_root, backend_log, port=backend_port) as client:
            health = client.get("/health")
            assert health.status_code == 200, health.text
            expired = client.get(f"/inference/sessions/{session_id}")
            assert expired.status_code == 404, expired.text

            session_row, persisted_steps = _persisted_inference_session(
                database_path, session_id
            )
            assert session_row[:3] == (5, "val00_lineage_20260921", 1000)
            assert session_row[3] is not None
            expected_steps = [
                (
                    step["step"],
                    step["bet_amount"],
                    step["predicted_action"],
                    step["predicted_relative_preference"],
                    step["observed_outcome_id"],
                    step["reward"],
                    step["capital_after"],
                )
                for step in original_snapshot["steps"]
            ]
            assert persisted_steps == expected_steps

            expected_expired_session_url = (
                f"{frontend_url}/api/inference/sessions/{session_id}"
            )
            page.reload(wait_until="domcontentloaded")
            page.locator(
                "#inference-checkpoint option[value='val00_lineage_20260921']"
            ).wait_for(state="attached")
            expect(page.get_by_role("button", name="Play", exact=True)).to_be_enabled()
            expect(page.get_by_role("button", name="Stop", exact=True)).to_be_disabled()
            expect(page.get_by_label("Observed value for step 1")).to_have_count(0)
            expect(rows).to_have_count(1)
            expect(page.locator("table tbody tr[aria-hidden='true']")).to_have_count(3)
            page.wait_for_function(
                "window.localStorage.getItem('fairs.roulette.inference-session.v1') === null"
            )
            assert page.evaluate(
                "window.localStorage.getItem('fairs.roulette.inference-session.v1')"
            ) is None
            page.screenshot(
                path=str(
                    PROJECT_ROOT
                    / "assets"
                    / "QA"
                    / "val14-inference-restart-recovered.png"
                ),
                full_page=True,
            )

            page.locator("#inference-checkpoint").select_option(
                "val00_lineage_20260921"
            )
            page.locator("#inference-dataset").select_option("5")
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith("/api/inference/sessions/start"),
                timeout=90_000,
            ) as fresh_start_info:
                page.get_by_role("button", name="Play", exact=True).click()
            fresh_start = fresh_start_info.value
            assert fresh_start.status == 200, fresh_start.text()
            fresh_session_id = str(fresh_start.json()["session_id"])
            assert fresh_session_id != session_id
            expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()

            stop_response = client.post(
                f"/inference/sessions/{fresh_session_id}/shutdown"
            )
            assert stop_response.status_code == 200, stop_response.text

    expired_session_failures = [
        result
        for result in failed_responses
        if expected_expired_session_url is not None
        and result == f"404 {expected_expired_session_url}"
    ]
    assert len(expired_session_failures) == 1, failed_responses
    unexpected_failures = [
        result
        for result in failed_responses
        if result != f"404 {expected_expired_session_url}"
    ]
    expected_404_console_message = (
        "Failed to load resource: the server responded with a status of 404 "
        "(Not Found)"
    )
    expected_reload_cancellations = [
        request
        for request in failed_requests
        if request.startswith("GET ") and request.endswith(": net::ERR_ABORTED")
    ]
    unexpected_failed_requests = [
        request for request in failed_requests if request not in expected_reload_cancellations
    ]
    assert page_errors == []
    assert console_errors == [expected_404_console_message]
    assert unexpected_failed_requests == [], failed_requests
    assert unexpected_failures == [], failed_responses
