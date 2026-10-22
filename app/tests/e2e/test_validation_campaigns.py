# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import re
import pytest
import hashlib
import sqlite3
import time
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import Page, expect, APIRequestContext
from server.common import path as shared_paths
from server.services.datasets import MAX_UPLOAD_SIZE_BYTES
from test_inference_workflows import get_session_snapshot, require_checkpoint, require_dataset_id, start_inference_session
from test_training_api import MINIMAL_TRAINING_CONFIG, VAL08_STORED_CPU_CONFIG, VAL10_LONG_STORED_CPU_CONFIG, assert_training_idle, incomplete_checkpoint_workspaces, wait_for_job_completion, wait_for_training_running, wait_for_training_stopped

"""Current-revision desktop evidence for the Training, Inference, and Settings pages."""




QA_ROOT = Path(__file__).resolve().parents[3] / "assets" / "QA"

###############################################################################
def _capture(page: Page, name: str) -> None:
    QA_ROOT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(QA_ROOT / name), full_page=False)

###############################################################################
def _assert_supported_desktop(page: Page, width: int, height: int) -> None:
    metrics = page.evaluate(
        """() => ({
            width: window.innerWidth,
            height: window.innerHeight,
            horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
        })"""
    )
    assert metrics == {
        "width": width,
        "height": height,
        "horizontalOverflow": False,
    }
    expect(page.locator(".desktop-size-notice")).to_be_hidden()

###############################################################################
@pytest.mark.val16_17
def test_desktop_page_views_and_minimum_width_boundary(page: Page, base_url: str):
    """Capture all principal pages at both supported desktop sizes and the 1099px gate."""
    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []
    failed_responses: list[str] = []
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

    routes = (
        (
            "training",
            "Training Monitor",
            "val17-training",
            (
                ("button", "Use generator"),
                ("heading", "Checkpoints"),
            ),
        ),
        (
            "inference",
            "Session History",
            "val17-inference",
            (
                ("combobox", "Model checkpoint"),
                ("combobox", "Inference dataset"),
            ),
        ),
        (
            "settings",
            "Roulette numbers",
            "val17-settings",
            (
                ("spinbutton", "Minimum"),
                ("spinbutton", "Maximum"),
                ("button", "Reset to defaults"),
            ),
        ),
    )

    for width, height in ((1440, 900), (1100, 800)):
        page.set_viewport_size({"width": width, "height": height})
        for route, heading, image_prefix, controls in routes:
            page.goto(f"{base_url}/{route}")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
            for role, name in controls:
                expect(page.get_by_role(role, name=name, exact=True)).to_be_visible()
            if route == "inference":
                expect(page.get_by_text("AI Suggestion", exact=False)).to_be_visible()
            _assert_supported_desktop(page, width, height)
            _capture(page, f"{image_prefix}-{width}x{height}.png")

    page.set_viewport_size({"width": 1099, "height": 800})
    page.goto(f"{base_url}/inference")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="Session History", exact=True)).to_be_visible()
    notice = page.locator(".desktop-size-notice")
    expect(notice).to_be_visible()
    expect(notice).to_contain_text("at least 1100px wide")
    boundary = page.evaluate(
        """() => {
            const root = document.querySelector('.inference-workspace > div');
            const panels = Array.from(root.children).map((panel) => panel.getBoundingClientRect());
            return {
                width: window.innerWidth,
                mainWidth: document.querySelector('.main-layout').getBoundingClientRect().width,
                columns: getComputedStyle(root).gridTemplateColumns.trim().split(/\\s+/).length,
                panelTopDelta: Math.abs(panels[0].top - panels[1].top),
            };
        }"""
    )
    assert boundary["width"] == 1099
    assert abs(boundary["mainWidth"] - 1100) < 1
    assert boundary["columns"] == 2
    assert boundary["panelTopDelta"] < 1
    _capture(page, "val17-inference-minimum-boundary-1099x800.png")

    assert page_errors == []
    assert console_errors == []
    assert failed_requests == []
    assert failed_responses == []

###############################################################################
@pytest.mark.val16_17
def test_training_setup_and_active_monitor_render(page: Page, base_url: str):
    """Exercise the stored-dataset wizard and capture a real active training monitor."""
    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []
    failed_responses: list[str] = []
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

    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{base_url}/training")
    page.wait_for_load_state("networkidle")

    configure_buttons = page.get_by_role(
        "button", name="Configure training with this dataset", exact=True
    )
    expect(configure_buttons.first).to_be_visible()
    database_count = configure_buttons.count()
    assert database_count >= 1, (
        "The stored dataset list should expose at least one configure action"
    )
    configure_buttons.nth(database_count - 1).click()
    wizard = page.get_by_role("dialog", name="New Training Wizard")
    expect(wizard).to_be_visible()
    wizard_position = wizard.evaluate(
        """dialog => {
            const rect = dialog.getBoundingClientRect();
            return {
                portaledToBody: dialog.parentElement?.parentElement === document.body,
                top: rect.top,
                bottom: rect.bottom,
                viewportHeight: window.innerHeight,
            };
        }"""
    )
    assert wizard_position["portaledToBody"]
    assert wizard_position["top"] >= 0
    assert wizard_position["bottom"] <= wizard_position["viewportHeight"]
    _capture(page, "val17-training-setup-1440x900.png")

    wizard.locator('input[name="perceptiveField"]').fill("8")
    for _ in range(5):
        wizard.get_by_role("button", name="Next", exact=True).click()
    checkpoint = f"val16_visual_{uuid4().hex[:10]}"
    wizard.locator('input[name="checkpointName"]').fill(checkpoint)
    expect(wizard.get_by_text("Episodes", exact=True)).to_be_visible()
    expect(wizard.get_by_text("Use GPU", exact=True)).to_be_visible()
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    wizard.evaluate(
        """dialog => {
            dialog.scrollTop = 0;
            dialog.querySelectorAll('*').forEach(element => { element.scrollTop = 0; });
        }"""
    )
    _capture(page, "val17-training-summary-1440x900.png")

    try:
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/training/start"),
            timeout=60_000,
        ) as start_info:
            wizard.get_by_role("button", name="Confirm", exact=True).click()
        start_response = start_info.value
        assert start_response.status == 202, start_response.text()

        stop_button = page.get_by_role("button", name="Stop", exact=True)
        expect(stop_button).to_be_enabled(timeout=30_000)
        page.wait_for_function(
            """() => /Episode\\s+\\d+\\s+\\/\\s+\\d+\\s+·\\s+Step\\s+[1-9]\\d*/
                .test(document.body.innerText)""",
            timeout=45_000,
        )
        page.get_by_role("heading", name="Training Monitor", exact=True).evaluate(
            "element => element.scrollIntoView({block: 'start', behavior: 'instant'})"
        )
        _capture(page, "val17-training-active-1440x900.png")
    finally:
        stop_button = page.get_by_role("button", name="Stop", exact=True)
        if stop_button.count() and stop_button.is_enabled():
            stop_button.click()
            expect(page.get_by_text("Training cancelled", exact=True)).to_be_visible(
                timeout=45_000
            )

    assert page_errors == []
    assert console_errors == []
    assert failed_requests == []
    assert failed_responses == []

###############################################################################
@pytest.mark.val16_17
def test_inference_active_session_render(page: Page, base_url: str):
    """Capture a live checkpoint-backed prediction and return the isolated app to idle."""
    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []
    failed_responses: list[str] = []
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

    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{base_url}/inference")
    page.wait_for_load_state("networkidle")
    page.locator("#inference-checkpoint").select_option("val00_lineage_20260921")
    page.locator("#inference-dataset").select_option("5")
    page.locator("#inference-initial-capital").fill("100")
    page.locator("#inference-bet-amount").fill("1")

    try:
        stop_button = page.get_by_role("button", name="Stop", exact=True)
        if stop_button.is_enabled():
            stop_button.click()
            expect(page.get_by_role("button", name="Play", exact=True)).to_be_enabled(
                timeout=15_000
            )

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/inference/sessions/start"),
            timeout=60_000,
        ) as start_info:
            page.get_by_role("button", name="Play", exact=True).click()
        start_response = start_info.value
        assert start_response.status == 200, start_response.text()
        rows = page.locator("table").get_by_role("row")
        expect(rows).to_have_count(2)
        prediction_text = rows.nth(1).get_by_role("cell").nth(1).inner_text()
        assert re.fullmatch(r"Bet on number \d+", prediction_text)
        expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()
        expect(page.get_by_role("heading", name="Session History", exact=True)).to_be_visible()
        _capture(page, "val17-inference-active-1440x900.png")
    finally:
        stop_button = page.get_by_role("button", name="Stop", exact=True)
        if stop_button.count() and stop_button.is_enabled():
            stop_button.click()
            expect(page.get_by_role("button", name="Play", exact=True)).to_be_enabled(
                timeout=15_000
            )

    assert page_errors == []
    assert console_errors == []
    assert failed_requests == []
    assert failed_responses == []


"""Tier 5 VAL-21 malformed-input and fail-closed recovery coverage."""




###############################################################################
def _assert_client_error(response) -> None:  # noqa: ANN001
    assert 400 <= response.status < 500, (
        f"Expected a deterministic 4xx, got {response.status}: {response.text()}"
    )

###############################################################################
def _assert_healthy(api_context: APIRequestContext) -> None:
    response = api_context.get("/api/health")
    assert response.status == 200, response.text()

###############################################################################
def _database_rows(query: str, parameters: tuple = ()) -> list[tuple]:
    with sqlite3.connect(shared_paths.DATABASE_PATH, timeout=5.0) as connection:
        return connection.execute(query, parameters).fetchall()

###############################################################################
def _dataset_state() -> tuple[list[tuple], list[tuple]]:
    datasets = _database_rows(
        "SELECT dataset_id, dataset_name, dataset_name_key, dataset_kind, "
        "created_at, updated_at FROM datasets ORDER BY dataset_id"
    )
    outcomes = _database_rows(
        "SELECT dataset_id, sequence_index, outcome_id "
        "FROM dataset_outcomes ORDER BY dataset_id, sequence_index"
    )
    return datasets, outcomes

###############################################################################
def _inference_persistence_state() -> tuple[list[tuple], list[tuple]]:
    sessions = _database_rows(
        "SELECT session_id, dataset_id, checkpoint_name, initial_capital, "
        "started_at, ended_at FROM inference_sessions ORDER BY session_id"
    )
    steps = _database_rows(
        "SELECT session_id, step_number, bet_amount, predicted_action, "
        "predicted_relative_preference, observed_outcome_id, reward, capital_after "
        "FROM inference_session_steps ORDER BY session_id, step_number"
    )
    return sessions, steps

###############################################################################
def _checkpoint_state(api_context: APIRequestContext) -> dict[str, dict[str, str]]:
    response = api_context.get("/api/training/checkpoints")
    assert response.status == 200, response.text()
    root = shared_paths.CHECKPOINT_PATH
    state: dict[str, dict[str, str]] = {}
    for name in response.json():
        checkpoint_root = root / name
        state[name] = {
            str(path.relative_to(checkpoint_root)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(checkpoint_root.rglob("*"))
            if path.is_file()
        }
    return state

###############################################################################
@pytest.mark.val21
def test_malformed_requests_are_4xx_and_leave_api_healthy(
    api_context: APIRequestContext,
) -> None:
    requests = [
        lambda: api_context.patch(
            "/api/settings",
            data="{",
            headers={"Content-Type": "application/json"},
        ),
        lambda: api_context.post("/api/training/validate", data={}),
        lambda: api_context.post(
            "/api/training/start", data={"episodes": "many"}
        ),
        lambda: api_context.post("/api/inference/sessions/start", data={}),
        lambda: api_context.post(
            "/api/inference/sessions/not-a-live-session/step",
            data={"extraction": 17},
        ),
    ]

    statuses: list[int] = []
    for request in requests:
        response = request()
        _assert_client_error(response)
        statuses.append(response.status)
        _assert_healthy(api_context)
    print(f"VAL21 malformed requests: responses={statuses}, health=200 after each")

###############################################################################
@pytest.mark.val21
def test_rejected_settings_patches_preserve_file_and_recover(
    api_context: APIRequestContext,
) -> None:
    before_response = api_context.get("/api/settings")
    assert before_response.status == 200, before_response.text()
    before_settings = before_response.json()

    invalid_patches = (
        {"database": {"host": "invalid.example"}},
        {"jobs": {"polling_interval": 0.01}},
        {"jobs": {"polling_interval": "fast"}},
        {"device": {"jit_backend": "unknown"}},
    )
    statuses: list[int] = []
    for patch in invalid_patches:
        response = api_context.patch("/api/settings", data=patch)
        _assert_client_error(response)
        statuses.append(response.status)
        assert api_context.get("/api/settings").json() == before_settings

    unchanged = api_context.get("/api/settings")
    assert unchanged.status == 200, unchanged.text()
    assert unchanged.json() == before_settings

    changed_interval = before_settings["jobs"]["polling_interval"] + 0.25
    update = api_context.patch(
        "/api/settings",
        data={"jobs": {"polling_interval": changed_interval}},
    )
    assert update.status == 200, update.text()
    assert update.json()["jobs"]["polling_interval"] == changed_interval

    restored = api_context.patch(
        "/api/settings",
        data={
            "jobs": {
                "polling_interval": before_settings["jobs"]["polling_interval"]
            }
        },
    )
    assert restored.status == 200, restored.text()
    assert restored.json() == before_settings
    _assert_healthy(api_context)
    print(f"VAL21 settings patches: rejected_statuses={statuses}, recovery=200")

###############################################################################
@pytest.mark.val21
def test_rejected_training_requests_create_no_jobs_or_checkpoints(
    api_context: APIRequestContext,
) -> None:
    before_status = api_context.get("/api/training/status")
    assert before_status.status == 200, before_status.text()
    assert before_status.json()["is_training"] is False
    before_datasets = _dataset_state()
    before_checkpoints = _checkpoint_state(api_context)

    rejected_checkpoint = f"val21_rejected_{uuid4().hex[:10]}"
    invalid_stored_dataset = dict(
        MINIMAL_TRAINING_CONFIG,
        dataset_id=999999999,
        use_data_generator=False,
        checkpoint_name=rejected_checkpoint,
    )
    requests = (
        lambda: api_context.post(
            "/api/training/validate",
            data="{",
            headers={"Content-Type": "application/json"},
        ),
        lambda: api_context.post(
            "/api/training/validate",
            data={"episodes": 0},
        ),
        lambda: api_context.post(
            "/api/training/start",
            data=invalid_stored_dataset,
        ),
    )
    statuses: list[int] = []
    for request in requests:
        response = request()
        _assert_client_error(response)
        statuses.append(response.status)
        status = api_context.get("/api/training/status")
        assert status.status == 200, status.text()
        assert status.json()["is_training"] is False
        assert status.json()["job_id"] is None

    after_status = api_context.get("/api/training/status")
    assert after_status.status == 200, after_status.text()
    assert after_status.json() == before_status.json()
    assert _dataset_state() == before_datasets
    assert _checkpoint_state(api_context) == before_checkpoints
    assert not list(shared_paths.CHECKPOINT_PATH.glob(".*.staging-*"))
    valid_validation = api_context.post(
        "/api/training/validate", data=MINIMAL_TRAINING_CONFIG
    )
    assert valid_validation.status == 200, valid_validation.text()
    assert api_context.get("/api/training/status").json() == before_status.json()
    _assert_healthy(api_context)
    print(
        "VAL21 training rejects: "
        f"statuses={statuses}, job_id=None, checkpoint={rejected_checkpoint} absent, "
        "staging=empty, valid_validation=200"
    )

###############################################################################
@pytest.mark.val21
def test_failed_uploads_are_transactional_and_valid_upload_recovers(
    api_context: APIRequestContext,
) -> None:
    summary_path = "/api/datasets/training/summary"
    before_response = api_context.get(summary_path)
    assert before_response.status == 200, before_response.text()
    before_datasets = before_response.json()["datasets"]
    before_state = _dataset_state()
    csv_bytes = b"draw_index,observed_outcome\n0,17\n1,21\n"
    invalid_requests = (
        lambda: api_context.post(
            "/api/data/upload?dataset_kind=unknown",
            multipart={
                "file": {
                    "name": "val21-invalid-kind.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_bytes,
                }
            },
        ),
        lambda: api_context.post(
            "/api/data/upload?dataset_kind=training&csv_separator=%2F",
            multipart={
                "file": {
                    "name": "val21-invalid-delimiter.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_bytes,
                }
            },
        ),
        lambda: api_context.post(
            "/api/data/upload?dataset_kind=training",
            multipart={
                "file": {
                    "name": "val21-no-valid-rows.csv",
                    "mimeType": "text/csv",
                    "buffer": b"draw_index,observed_outcome\n0,999\n1,-4\n",
                }
            },
        ),
        lambda: api_context.post(
            "/api/data/upload?dataset_kind=training",
            multipart={
                "file": {
                    "name": "val21-corrupt.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "buffer": b"not-an-xlsx-archive",
                }
            },
        ),
        lambda: api_context.post(
            "/api/data/upload?dataset_kind=training",
            multipart={
                "file": {
                    "name": "val21-oversized.csv",
                    "mimeType": "text/csv",
                    "buffer": b"x" * (MAX_UPLOAD_SIZE_BYTES + 1),
                }
            },
        ),
        lambda: api_context.post(
            "/api/data/upload?dataset_kind=training",
            multipart={
                "file": {
                    "name": f"{'a' * 256}.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_bytes,
                }
            },
        ),
    )
    statuses: list[int] = []
    for request in invalid_requests:
        response = request()
        _assert_client_error(response)
        statuses.append(response.status)
        assert _dataset_state() == before_state
        assert api_context.get(summary_path).json()["datasets"] == before_datasets

    dataset_name = f"val21_recovery_{uuid4().hex[:10]}"
    upload = api_context.post(
        "/api/data/upload?dataset_kind=training&csv_separator=%2C",
        multipart={
            "file": {
                "name": f"{dataset_name}.csv",
                "mimeType": "text/csv",
                "buffer": csv_bytes,
            }
        },
    )
    assert upload.status == 200, upload.text()
    dataset_id = upload.json()["dataset_id"]
    try:
        assert upload.json()["rows_imported"] == 2
        delete = api_context.delete(f"/api/datasets/training/{dataset_id}")
        assert delete.status == 200, delete.text()
    finally:
        remaining = api_context.get(summary_path)
        if remaining.ok and any(
            dataset.get("dataset_id") == dataset_id
            for dataset in remaining.json().get("datasets", [])
        ):
            cleanup = api_context.delete(
                f"/api/datasets/training/{dataset_id}"
            )
            assert cleanup.status == 200, cleanup.text()

    assert _dataset_state() == before_state
    assert api_context.get(summary_path).json()["datasets"] == before_datasets
    _assert_healthy(api_context)
    print(
        "VAL21 upload rejects/recovery: "
        f"rejected_statuses={statuses}, recovered_dataset_id={dataset_id}, "
        f"name={dataset_name}, rows_imported=2, cleanup=complete"
    )

###############################################################################
@pytest.mark.val21
def test_inference_rejections_preserve_live_session_and_recover(
    api_context: APIRequestContext,
) -> None:
    checkpoint = require_checkpoint(api_context)
    dataset_id = require_dataset_id(api_context)
    started = start_inference_session(api_context, checkpoint, dataset_id)
    session_id = started["session_id"]
    before_snapshot = get_session_snapshot(api_context, session_id)
    before_persistence = _inference_persistence_state()

    def assert_session_unchanged() -> None:
        assert get_session_snapshot(api_context, session_id) == before_snapshot
        assert _inference_persistence_state() == before_persistence

    try:
        invalid_starts = (
            lambda: api_context.post(
                "/api/inference/sessions/start",
                data={
                    "checkpoint": "val21_missing_checkpoint",
                    "dataset_id": dataset_id,
                    "game_capital": 1000,
                    "game_bet": 10,
                },
            ),
            lambda: api_context.post(
                "/api/inference/sessions/start",
                data={
                    "checkpoint": checkpoint,
                    "dataset_id": 999999999,
                    "game_capital": 1000,
                    "game_bet": 10,
                },
            ),
        )
        invalid_start_statuses: list[int] = []
        for request in invalid_starts:
            response = request()
            assert response.status == 404, response.text()
            invalid_start_statuses.append(response.status)
            assert_session_unchanged()
            _assert_healthy(api_context)

        invalid_operations = (
            lambda: api_context.post(
                f"/api/inference/sessions/{session_id}/step",
                data={"extraction": 37},
            ),
            lambda: api_context.post(
                f"/api/inference/sessions/{session_id}/step",
                data={"extraction": "not-a-number"},
            ),
            lambda: api_context.post(
                f"/api/inference/sessions/{session_id}/bet",
                data={"bet_amount": 0},
            ),
            lambda: api_context.post(
                "/api/inference/sessions/val21_stale_session/step",
                data={"extraction": 17},
            ),
        )
        invalid_statuses: list[int] = []
        for request in invalid_operations:
            response = request()
            _assert_client_error(response)
            invalid_statuses.append(response.status)
            assert_session_unchanged()
            _assert_healthy(api_context)

        updated_bet = api_context.post(
            f"/api/inference/sessions/{session_id}/bet",
            data={"bet_amount": 25},
        )
        assert updated_bet.status == 200, updated_bet.text()
        step = api_context.post(
            f"/api/inference/sessions/{session_id}/step",
            data={"extraction": 17},
        )
        assert step.status == 200, step.text()
    finally:
        api_context.post(f"/api/inference/sessions/{session_id}/shutdown")

    recovery = start_inference_session(
        api_context,
        checkpoint,
        dataset_id,
        game_capital=1200,
        game_bet=15,
    )
    recovery_id = recovery["session_id"]
    try:
        assert recovery_id != session_id
        snapshot = get_session_snapshot(api_context, recovery_id)
        assert snapshot["current_capital"] == 1200
        assert snapshot["current_bet"] == 15
        assert snapshot["step_count"] == 0
    finally:
        api_context.post(f"/api/inference/sessions/{recovery_id}/shutdown")

    ended = _database_rows(
        "SELECT ended_at FROM inference_sessions WHERE session_id = ?",
        (session_id,),
    )
    assert ended and ended[0][0] is not None
    _assert_healthy(api_context)
    print(
        "VAL21 inference rejects/recovery: "
        f"checkpoint={checkpoint}, dataset_id={dataset_id}, "
        f"invalid_start_statuses={invalid_start_statuses}, "
        f"rejected_statuses={invalid_statuses}, "
        f"failed_session_id={session_id}, recovery_session_id={recovery_id}, ended=yes"
    )


"""Tier 5 VAL-22 repetition, bounded execution, and state-leak coverage."""




###############################################################################
def _active_sessions() -> tuple[str, ...]:
    with sqlite3.connect(shared_paths.DATABASE_PATH, timeout=5.0) as connection:
        rows = connection.execute(
            "SELECT session_id FROM inference_sessions "
            "WHERE ended_at IS NULL ORDER BY session_id"
        ).fetchall()
    return tuple(row[0] for row in rows)

###############################################################################
def _ended_session(session_id: str) -> tuple | None:
    with sqlite3.connect(shared_paths.DATABASE_PATH, timeout=5.0) as connection:
        return connection.execute(
            "SELECT ended_at, initial_capital FROM inference_sessions "
            "WHERE session_id = ?",
            (session_id,),
        ).fetchone()

###############################################################################
def _start_replacement_session(
    api_context: APIRequestContext,
    checkpoint: str,
    dataset_id: int,
    initial_capital: int,
    initial_bet: int,
    preserve_session_id: str,
) -> dict:
    response = api_context.post(
        "/api/inference/sessions/start",
        headers={"X-Preserve-Inference-Session": preserve_session_id},
        data={
            "checkpoint": checkpoint,
            "dataset_id": dataset_id,
            "game_capital": initial_capital,
            "game_bet": initial_bet,
        },
    )
    assert response.status == 200, response.text()
    return response.json()

###############################################################################
def _training_staging_directories() -> tuple[str, ...]:
    root = shared_paths.CHECKPOINT_PATH
    markers = (".staging-", ".backup-", ".publish-")
    if not root.exists():
        return ()
    return tuple(
        sorted(
            entry.name
            for entry in root.iterdir()
            if entry.is_dir() and any(marker in entry.name for marker in markers)
        )
    )

###############################################################################
@pytest.mark.val22
def test_repeated_inference_cycles_do_not_leak_session_state(
    api_context: APIRequestContext,
) -> None:
    checkpoint = require_checkpoint(api_context)
    dataset_id = require_dataset_id(api_context)
    baseline_sessions = _active_sessions()
    assert baseline_sessions == ()
    baseline_checkpoints = api_context.get("/api/training/checkpoints").json()
    cycle_durations: list[float] = []
    session_ids: list[str] = []

    for cycle in range(3):
        initial_capital = 1200 + cycle * 100
        initial_bet = 5 + cycle
        cycle_session_ids: list[str] = []
        started_at = time.perf_counter()
        started = start_inference_session(
            api_context,
            checkpoint,
            dataset_id,
            game_capital=initial_capital,
            game_bet=initial_bet,
        )
        session_id = started["session_id"]
        session_ids.append(session_id)
        cycle_session_ids.append(session_id)
        current_session_id = session_id
        try:
            initial = get_session_snapshot(api_context, session_id)
            assert initial["current_capital"] == initial_capital
            assert initial["current_bet"] == initial_bet
            assert initial["step_count"] == 0

            bet = initial_bet + 10
            bet_response = api_context.post(
                f"/api/inference/sessions/{session_id}/bet",
                data={"bet_amount": bet},
            )
            assert bet_response.status == 200, bet_response.text()
            first_outcome = 17 + cycle
            first_step = api_context.post(
                f"/api/inference/sessions/{session_id}/step",
                data={"extraction": first_outcome},
            )
            assert first_step.status == 200, first_step.text()
            next_prediction = api_context.post(
                f"/api/inference/sessions/{session_id}/next"
            )
            assert next_prediction.status == 200, next_prediction.text()
            second_outcome = 21 + cycle
            second_step = api_context.post(
                f"/api/inference/sessions/{session_id}/step",
                data={"extraction": second_outcome},
            )
            assert second_step.status == 200, second_step.text()

            corrected_outcome = (first_outcome + 1) % 37
            corrected = _start_replacement_session(
                api_context,
                checkpoint,
                dataset_id,
                initial_capital,
                bet,
                current_session_id,
            )
            previous_session_id = current_session_id
            current_session_id = corrected["session_id"]
            cycle_session_ids.append(current_session_id)
            session_ids.append(current_session_id)
            corrected_initial = get_session_snapshot(api_context, current_session_id)
            assert corrected_initial["initial_capital"] == initial_capital
            assert corrected_initial["current_bet"] == bet
            assert corrected_initial["step_count"] == 0

            corrected_step = api_context.post(
                f"/api/inference/sessions/{current_session_id}/step",
                data={"extraction": corrected_outcome},
            )
            assert corrected_step.status == 200, corrected_step.text()
            corrected_next = api_context.post(
                f"/api/inference/sessions/{current_session_id}/next"
            )
            assert corrected_next.status == 200, corrected_next.text()
            replayed_step = api_context.post(
                f"/api/inference/sessions/{current_session_id}/step",
                data={"extraction": second_outcome},
            )
            assert replayed_step.status == 200, replayed_step.text()

            old_shutdown = api_context.post(
                f"/api/inference/sessions/{previous_session_id}/shutdown"
            )
            assert old_shutdown.status == 200, old_shutdown.text()
            assert api_context.post(
                f"/api/inference/sessions/{previous_session_id}/next"
            ).status == 404
            corrected_snapshot = get_session_snapshot(api_context, current_session_id)
            assert corrected_snapshot["step_count"] == 2
            assert [
                step["observed_outcome_id"]
                for step in corrected_snapshot["steps"]
            ] == [corrected_outcome, second_outcome]

            removed = _start_replacement_session(
                api_context,
                checkpoint,
                dataset_id,
                initial_capital,
                bet,
                current_session_id,
            )
            previous_session_id = current_session_id
            current_session_id = removed["session_id"]
            cycle_session_ids.append(current_session_id)
            session_ids.append(current_session_id)
            removed_initial = get_session_snapshot(api_context, current_session_id)
            assert removed_initial["initial_capital"] == initial_capital
            assert removed_initial["current_bet"] == bet
            assert removed_initial["step_count"] == 0
            removed_step = api_context.post(
                f"/api/inference/sessions/{current_session_id}/step",
                data={"extraction": corrected_outcome},
            )
            assert removed_step.status == 200, removed_step.text()

            old_shutdown = api_context.post(
                f"/api/inference/sessions/{previous_session_id}/shutdown"
            )
            assert old_shutdown.status == 200, old_shutdown.text()
            assert api_context.post(
                f"/api/inference/sessions/{previous_session_id}/next"
            ).status == 404
            removed_snapshot = get_session_snapshot(api_context, current_session_id)
            assert removed_snapshot["step_count"] == 1
            assert [
                step["observed_outcome_id"]
                for step in removed_snapshot["steps"]
            ] == [corrected_outcome]
        finally:
            for created_session_id in reversed(cycle_session_ids):
                shutdown = api_context.post(
                    f"/api/inference/sessions/{created_session_id}/shutdown"
                )
                assert shutdown.status == 200, shutdown.text()

        for created_session_id in cycle_session_ids:
            persisted = _ended_session(created_session_id)
            assert persisted is not None and persisted[0] is not None
            clear = api_context.post(
                f"/api/inference/sessions/{created_session_id}/rows/clear"
            )
            assert clear.status == 200, clear.text()
            with sqlite3.connect(
                shared_paths.DATABASE_PATH, timeout=5.0
            ) as connection:
                remaining_steps = connection.execute(
                    "SELECT COUNT(*) FROM inference_session_steps WHERE session_id = ?",
                    (created_session_id,),
                ).fetchone()[0]
            assert remaining_steps == 0

        cycle_durations.append(time.perf_counter() - started_at)
        assert _active_sessions() == baseline_sessions
        assert all(
            api_context.get(f"/api/inference/sessions/{created_session_id}").status
            == 404
            for created_session_id in cycle_session_ids
        )
        assert _ended_session(session_id)[1] == initial_capital

    assert len(session_ids) == len(cycle_durations) * 3
    assert len(set(session_ids)) == len(session_ids)
    assert api_context.get("/api/training/checkpoints").json() == baseline_checkpoints
    print(
        "VAL22 inference cycles: "
        f"checkpoint={checkpoint}, dataset_id={dataset_id}, session_ids={session_ids}, "
        f"count={len(cycle_durations)}, total={sum(cycle_durations):.3f}s, "
        f"per_cycle={[round(value, 3) for value in cycle_durations]}, "
        f"max={max(cycle_durations):.3f}s, request_timeout=30s, "
        f"active_after={_active_sessions()}"
    )

###############################################################################
@pytest.mark.val22
def test_repeated_settings_writes_remain_parseable_and_leave_no_temp_files(
    api_context: APIRequestContext,
) -> None:
    before_response = api_context.get("/api/settings")
    assert before_response.status == 200, before_response.text()
    before = before_response.json()
    reset_defaults: dict | None = None
    intervals: list[float] = []
    cycle_durations: list[float] = []

    try:
        for cycle in range(10):
            interval = 0.5 + (cycle % 5) * 0.25
            started_at = time.perf_counter()
            updated = api_context.patch(
                "/api/settings",
                data={"jobs": {"polling_interval": interval}},
            )
            assert updated.status == 200, updated.text()
            read_back = api_context.get("/api/settings")
            assert read_back.status == 200, read_back.text()
            assert read_back.json()["jobs"]["polling_interval"] == interval

            reset = api_context.post("/api/settings/reset")
            assert reset.status == 200, reset.text()
            if reset_defaults is None:
                reset_defaults = reset.json()
                assert reset_defaults == {
                    "jobs": {"polling_interval": 1.0},
                    "device": {"jit_compile": False, "jit_backend": "eager"},
                    "roulette": {
                        "minimum_number": 0,
                        "maximum_number": 36,
                        "exclude_zero": False,
                        "invert_colors": False,
                        "show_number_labels": True,
                    },
                }
            else:
                assert reset.json() == reset_defaults
            reset_read = api_context.get("/api/settings")
            assert reset_read.status == 200, reset_read.text()
            assert reset_read.json() == reset_defaults
            intervals.append(interval)
            cycle_durations.append(time.perf_counter() - started_at)
    finally:
        restore = api_context.patch(
            "/api/settings",
            data={
                "jobs": {
                    "polling_interval": before["jobs"]["polling_interval"]
                },
                "device": before["device"],
            },
        )
        assert restore.status == 200, restore.text()

    final = api_context.get("/api/settings")
    assert final.status == 200, final.text()
    assert final.json() == before
    print(
        "VAL22 settings cycles: "
        f"count={len(cycle_durations)}, total={sum(cycle_durations):.3f}s, "
        f"per_cycle={[round(value, 3) for value in cycle_durations]}, "
        f"max={max(cycle_durations):.3f}s, request_timeout=30s, values={intervals}, "
        f"reset_count={len(cycle_durations)}, "
        f"final_polling_interval={final.json()['jobs']['polling_interval']}, database_row=active"
    )

###############################################################################
@pytest.mark.val22
def test_repeated_training_cancellation_returns_to_idle_and_recovers(
    api_context: APIRequestContext,
) -> None:
    assert_training_idle(api_context)
    baseline_checkpoints = api_context.get("/api/training/checkpoints").json()
    baseline_staging = _training_staging_directories()
    cycle_durations: list[float] = []
    disposable_checkpoints: list[str] = []
    cancelled_job_ids: list[str] = []
    recovery_job_ids: list[str] = []

    try:
        for cycle in range(3):
            started_at = time.perf_counter()
            checkpoint = f"val22_cancel_{uuid4().hex[:10]}"
            recovery_checkpoint = f"val22_recovery_{uuid4().hex[:10]}"
            disposable_checkpoints.extend((checkpoint, recovery_checkpoint))
            start = api_context.post(
                "/api/training/start",
                data=dict(VAL10_LONG_STORED_CPU_CONFIG, checkpoint_name=checkpoint),
            )
            assert start.status == 202, start.text()
            job_id = start.json()["job_id"]
            cancelled_job_ids.append(job_id)
            assert wait_for_training_running(api_context, timeout=45.0), (
                api_context.get("/api/training/status").json()
            )

            cancelled = api_context.delete(
                f"/api/training/jobs/{job_id}"
            )
            assert cancelled.status == 200, cancelled.text()
            terminal = wait_for_job_completion(
                api_context, job_id, timeout=45.0
            )
            assert terminal.get("status") == "cancelled", terminal
            assert_training_idle(api_context)
            assert checkpoint not in api_context.get(
                "/api/training/checkpoints"
            ).json()
            assert incomplete_checkpoint_workspaces(checkpoint) == []

            recovery = api_context.post(
                "/api/training/start",
                data=dict(VAL08_STORED_CPU_CONFIG, checkpoint_name=recovery_checkpoint),
            )
            assert recovery.status == 202, recovery.text()
            recovery_job_id = recovery.json()["job_id"]
            recovery_job_ids.append(recovery_job_id)
            recovered = wait_for_job_completion(
                api_context, recovery_job_id, timeout=90.0
            )
            assert recovered.get("status") == "completed", recovered
            assert_training_idle(api_context)
            assert recovery_checkpoint in api_context.get(
                "/api/training/checkpoints"
            ).json()
            cycle_durations.append(time.perf_counter() - started_at)

            delete = api_context.delete(
                f"/api/training/checkpoints/{recovery_checkpoint}"
            )
            assert delete.status == 200, delete.text()

        assert api_context.get("/api/training/checkpoints").json() == baseline_checkpoints
        assert _training_staging_directories() == baseline_staging
        assert not api_context.get("/api/training/status").json()["is_training"]
    finally:
        api_context.post("/api/training/stop")
        wait_for_training_stopped(api_context, timeout=30.0)
        for checkpoint in disposable_checkpoints:
            names = api_context.get("/api/training/checkpoints")
            if names.ok and checkpoint in names.json():
                api_context.delete(f"/api/training/checkpoints/{checkpoint}")

    print(
        "VAL22 training cycles: "
        f"cancelled_job_ids={cancelled_job_ids}, recovery_job_ids={recovery_job_ids}, "
        f"checkpoints={disposable_checkpoints}, "
        f"count={len(cycle_durations)}, total={sum(cycle_durations):.3f}s, "
        f"per_cycle={[round(value, 3) for value in cycle_durations]}, "
        f"max={max(cycle_durations):.3f}s, cancel_timeout=45s, "
        f"recovery_timeout=90s, active_after="
        f"{api_context.get('/api/training/status').json()['is_training']}"
    )
