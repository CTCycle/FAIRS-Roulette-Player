# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import pytest
import json
import os
import sqlite3
from playwright.sync_api import APIRequestContext, Page, expect
from pathlib import Path

"""
E2E tests for Inference API endpoints.
Tests: /inference/sessions/start, /inference/sessions/{id}/next,
       /inference/sessions/{id}/step, /inference/sessions/{id}/shutdown
"""


VAL11_CHECKPOINT = "val00_lineage_20260921"
VAL11_DATASET_ID = 5


###############################################################################
def require_checkpoint(api_context: APIRequestContext) -> str:
    response = api_context.get("/api/training/checkpoints")
    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    checkpoints = response.json()
    if VAL11_CHECKPOINT not in checkpoints:
        pytest.skip(f"VAL-11 checkpoint {VAL11_CHECKPOINT!r} is not available.")
    return VAL11_CHECKPOINT


###############################################################################
def require_dataset_id(api_context: APIRequestContext) -> int:
    response = api_context.get("/api/datasets/training")
    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    datasets = response.json().get("datasets", [])
    dataset = next(
        (
            item
            for item in datasets
            if item.get("dataset_id") == VAL11_DATASET_ID
        ),
        None,
    )
    if dataset is None:
        pytest.skip(f"VAL-11 training dataset {VAL11_DATASET_ID} is not available.")
    return VAL11_DATASET_ID


###############################################################################
def start_inference_session(
    api_context: APIRequestContext,
    checkpoint: str,
    dataset_id: int,
    game_capital: int = 1000,
    game_bet: int = 10,
) -> dict:
    response = api_context.post(
        "/api/inference/sessions/start",
        data={
            "checkpoint": checkpoint,
            "dataset_id": dataset_id,
            "game_capital": game_capital,
            "game_bet": game_bet,
        },
    )
    if not response.ok:
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            payload = {}
        detail = (
            payload.get("detail", response.text())
            if isinstance(payload, dict)
            else response.text()
        )
        pytest.fail(
            f"Unable to start inference session with the VAL-11 lineage: {detail}",
            pytrace=False,
        )
    return response.json()


###############################################################################
def get_session_snapshot(
    api_context: APIRequestContext, session_id: str
) -> dict:
    response = api_context.get(f"/api/inference/sessions/{session_id}")
    assert response.ok, f"Expected 200, got {response.status}: {response.text()}"
    return response.json()


###############################################################################
class TestInferenceEndpoints:
    """Tests for the /inference/* API endpoints."""

    # -------------------------------------------------------------------------
    def test_start_session_with_invalid_checkpoint_returns_404(
        self, api_context: APIRequestContext
    ):
        """POST /inference/sessions/start with invalid checkpoint should return 404."""
        response = api_context.post(
            "/api/inference/sessions/start",
            data={
                "checkpoint": "non_existent_checkpoint_xyz",
                "dataset_id": 999999,
                "game_capital": 1000,
                "game_bet": 10,
            },
        )
        # Expect 404 because checkpoint doesn't exist
        assert response.status == 404

        data = response.json()
        assert "detail" in data

    # -------------------------------------------------------------------------
    def test_get_next_prediction_invalid_session_returns_404(
        self, api_context: APIRequestContext
    ):
        """POST /inference/sessions/{invalid_id}/next should return 404."""
        response = api_context.post(
            "/api/inference/sessions/invalid_session_id_12345/next"
        )
        assert response.status == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    # -------------------------------------------------------------------------
    def test_submit_step_invalid_session_returns_404(
        self, api_context: APIRequestContext
    ):
        """POST /inference/sessions/{invalid_id}/step should return 404."""
        response = api_context.post(
            "/api/inference/sessions/invalid_session_id_12345/step",
            data={
                "extraction": 17,
            },
        )
        assert response.status == 404

    # -------------------------------------------------------------------------
    def test_shutdown_invalid_session_succeeds(self, api_context: APIRequestContext):
        """
        POST /inference/sessions/{invalid_id}/shutdown should succeed (idempotent).
        Shutting down a non-existent session should not fail.
        """
        response = api_context.post("/api/inference/sessions/any_session_id/shutdown")
        # The current implementation deletes from dict silently, so it returns 200
        assert response.ok

        data = response.json()
        assert data.get("status") == "closed"

    # -------------------------------------------------------------------------
    def test_update_bet_invalid_session_returns_404(
        self, api_context: APIRequestContext
    ):
        response = api_context.post(
            "/api/inference/sessions/invalid_session_id_12345/bet",
            data={"bet_amount": 25},
        )
        assert response.status == 404
        data = response.json()
        assert "detail" in data

    # -------------------------------------------------------------------------
    def test_clear_rows_on_unknown_session_is_idempotent(
        self, api_context: APIRequestContext
    ):
        response = api_context.post("/api/inference/sessions/non_existent/rows/clear")
        assert response.ok
        data = response.json()
        assert data.get("status") == "cleared"
        assert data.get("session_id") == "non_existent"


###############################################################################
class TestInferenceSessionFlow:
    """
    Integration tests for the full inference session lifecycle.
    These tests require a valid checkpoint to exist.
    """

    # -------------------------------------------------------------------------
    def test_full_inference_session_flow(self, api_context: APIRequestContext):
        """
        Tests the complete lifecycle: start -> step -> next -> shutdown.
        Uses the fixed VAL-00 training lineage when it is available.
        """
        checkpoint_name = require_checkpoint(api_context)
        dataset_id = require_dataset_id(api_context)
        start_data = start_inference_session(api_context, checkpoint_name, dataset_id)
        session_id = start_data["session_id"]
        assert isinstance(session_id, str) and session_id
        assert start_data.get("checkpoint") == checkpoint_name
        assert start_data.get("game_capital") == 1000
        assert start_data.get("game_bet") >= 1
        assert start_data.get("current_capital") <= 1000
        prediction = start_data.get("prediction")
        assert isinstance(prediction, dict)
        assert isinstance(prediction.get("action"), int)
        assert isinstance(prediction.get("description"), str)
        relative_preference = prediction.get("relative_preference")
        assert isinstance(relative_preference, (int, float))
        assert 0.0 <= float(relative_preference) <= 1.0
        assert "confidence" not in prediction

        try:
            initial_snapshot = get_session_snapshot(api_context, session_id)
            assert initial_snapshot.get("checkpoint") == checkpoint_name
            assert initial_snapshot.get("dataset_id") == dataset_id
            assert initial_snapshot.get("initial_capital") == 1000
            assert initial_snapshot.get("step_count") == 0
            assert initial_snapshot.get("prediction_pending") is True
            assert initial_snapshot.get("last_prediction") == prediction
            assert len(initial_snapshot.get("steps", [])) == 1

            bet_response = api_context.post(
                f"/api/inference/sessions/{session_id}/bet",
                data={"bet_amount": 25},
            )
            assert bet_response.ok, (
                f"Expected 200, got {bet_response.status}: {bet_response.text()}"
            )
            assert bet_response.json().get("bet_amount") == 25
            bet_snapshot = get_session_snapshot(api_context, session_id)
            assert bet_snapshot.get("current_bet") == 25
            assert bet_snapshot.get("step_count") == 0
            assert bet_snapshot["steps"][0].get("bet_amount") == 25

            # Submit the observed result for the initial prediction.
            step_response = api_context.post(
                f"/api/inference/sessions/{session_id}/step",
                data={
                    "extraction": 17,
                },
            )
            assert step_response.ok
            step_data = step_response.json()
            assert "step" in step_data
            assert "reward" in step_data
            assert "capital_after" in step_data
            assert step_data.get("session_id") == session_id
            assert step_data.get("step") == 1
            assert step_data.get("real_extraction") == 17
            assert isinstance(step_data.get("predicted_action"), int)
            assert isinstance(step_data.get("predicted_action_desc"), str)
            assert isinstance(step_data.get("reward"), int)
            assert isinstance(step_data.get("capital_after"), int)

            observed_snapshot = get_session_snapshot(api_context, session_id)
            assert observed_snapshot.get("step_count") == 1
            assert observed_snapshot.get("prediction_pending") is False
            assert observed_snapshot.get("current_capital") == step_data["capital_after"]
            assert len(observed_snapshot.get("steps", [])) == 1
            assert observed_snapshot["steps"][0].get("bet_amount") == 25
            assert observed_snapshot["steps"][0].get("observed_outcome_id") == 17
            assert observed_snapshot["steps"][0].get("reward") == step_data["reward"]
            assert (
                observed_snapshot["steps"][0].get("capital_after")
                == step_data["capital_after"]
            )

            # Request the next prediction only after the observed result.
            next_response = api_context.post(
                f"/api/inference/sessions/{session_id}/next"
            )
            assert next_response.ok
            next_data = next_response.json()
            assert "prediction" in next_data
            assert next_data["prediction"] is not None
            assert next_data.get("session_id") == session_id
            assert isinstance(next_data["prediction"].get("action"), int)
            assert isinstance(next_data["prediction"].get("description"), str)
            next_preference = next_data["prediction"].get("relative_preference")
            assert isinstance(next_preference, (int, float))
            assert 0.0 <= float(next_preference) <= 1.0
            assert "confidence" not in next_data["prediction"]

            next_snapshot = get_session_snapshot(api_context, session_id)
            assert next_snapshot.get("step_count") == 1
            assert next_snapshot.get("prediction_pending") is True
            assert next_snapshot.get("last_prediction") == next_data["prediction"]
            assert len(next_snapshot.get("steps", [])) == 2
            assert next_snapshot["steps"][0].get("observed_outcome_id") == 17
            assert next_snapshot["steps"][1].get("observed_outcome_id") is None

        finally:
            # Always shutdown the session
            shutdown_response = api_context.post(
                f"/api/inference/sessions/{session_id}/shutdown"
            )
            assert shutdown_response.ok, (
                f"Expected 200, got {shutdown_response.status}: {shutdown_response.text()}"
            )

    # -------------------------------------------------------------------------
    def test_inference_session_supports_bet_update_and_rows_clear(
        self, api_context: APIRequestContext
    ):
        checkpoint_name = require_checkpoint(api_context)
        dataset_id = require_dataset_id(api_context)
        start_data = start_inference_session(api_context, checkpoint_name, dataset_id)
        session_id = start_data["session_id"]

        try:
            bet_response = api_context.post(
                f"/api/inference/sessions/{session_id}/bet",
                data={"bet_amount": 25},
            )
            assert bet_response.ok, (
                f"Expected 200, got {bet_response.status}: {bet_response.text()}"
            )
            bet_payload = bet_response.json()
            assert bet_payload.get("session_id") == session_id
            assert bet_payload.get("bet_amount") == 25
            bet_snapshot = get_session_snapshot(api_context, session_id)
            assert bet_snapshot.get("current_bet") == 25
            assert bet_snapshot.get("step_count") == 0
            assert len(bet_snapshot.get("steps", [])) == 1

            shutdown_response = api_context.post(
                f"/api/inference/sessions/{session_id}/shutdown"
            )
            assert shutdown_response.ok

            clear_rows_response = api_context.post(
                f"/api/inference/sessions/{session_id}/rows/clear"
            )
            assert clear_rows_response.ok, (
                f"Expected 200, got {clear_rows_response.status}: {clear_rows_response.text()}"
            )
            clear_rows_payload = clear_rows_response.json()
            assert clear_rows_payload.get("session_id") == session_id
            assert clear_rows_payload.get("status") == "cleared"
        finally:
            api_context.post(f"/api/inference/sessions/{session_id}/shutdown")

    # -------------------------------------------------------------------------
    def test_clear_inference_context_removes_uploaded_inference_dataset(
        self, api_context: APIRequestContext
    ):
        """Run against isolated app data because context clear removes all uploads."""
        checkpoint_name = require_checkpoint(api_context)
        csv_content = b"outcome\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10"
        upload_response = api_context.post(
            "/api/data/upload?dataset_kind=inference&csv_separator=%2C",
            multipart={
                "file": {
                    "name": "val11_inference_context_clear.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content,
                }
            },
        )
        assert upload_response.ok, (
            f"Expected 200, got {upload_response.status}: {upload_response.text()}"
        )
        upload_payload = upload_response.json()
        dataset_id = upload_payload.get("dataset_id")
        assert isinstance(dataset_id, int) and dataset_id > 0

        clear_response = api_context.post("/api/inference/context/clear")
        assert clear_response.ok, (
            f"Expected 200, got {clear_response.status}: {clear_response.text()}"
        )
        clear_payload = clear_response.json()
        assert clear_payload.get("status") == "cleared"

        start_response = api_context.post(
            "/api/inference/sessions/start",
            data={
                "checkpoint": checkpoint_name,
                "dataset_id": dataset_id,
                "game_capital": 1000,
                "game_bet": 10,
            },
        )
        assert start_response.status == 404
        start_payload = start_response.json()
        assert "detail" in start_payload
        assert "dataset" in str(start_payload["detail"]).lower()

    # -------------------------------------------------------------------------
    def test_clear_inference_context_rejects_active_session(
        self, api_context: APIRequestContext
    ):
        checkpoint_name = require_checkpoint(api_context)
        dataset_id = require_dataset_id(api_context)
        start_data = start_inference_session(api_context, checkpoint_name, dataset_id)
        session_id = start_data["session_id"]

        try:
            clear_response = api_context.post("/api/inference/context/clear")
            assert clear_response.status == 409
            payload = clear_response.json()
            assert "active" in str(payload.get("detail", "")).lower()
        finally:
            shutdown_response = api_context.post(
                f"/api/inference/sessions/{session_id}/shutdown"
            )
            assert shutdown_response.ok


"""Live browser coverage for learned inference betting suggestions."""




VAL15_CHECKPOINT = os.getenv("FAIRS_VAL15_CHECKPOINT", "val15_strategy_20260923")
VAL15_DATASET_ID = 5
STRATEGY_NAMES = {
    0: "Keep",
    1: "Martingale",
    2: "Reverse",
    3: "DAlembert",
    4: "Fibonacci",
}


###############################################################################
def _data_root() -> Path:
    configured = os.getenv("FAIRS_DATA_DIR", "").strip()
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[3] / "data"


###############################################################################
def _persisted_steps(session_id: str) -> list[tuple[object, ...]]:
    database_path = _data_root() / "database.db"
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as database:
        return database.execute(
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


###############################################################################
def _require_val15_fixture(api_context: APIRequestContext) -> str:
    checkpoints_response = api_context.get("/api/training/checkpoints")
    assert checkpoints_response.ok, checkpoints_response.text()
    if VAL15_CHECKPOINT not in checkpoints_response.json():
        pytest.skip(f"VAL-15 strategy checkpoint {VAL15_CHECKPOINT!r} is unavailable.")

    datasets_response = api_context.get("/api/datasets/training")
    assert datasets_response.ok, datasets_response.text()
    dataset_ids = {
        dataset.get("dataset_id")
        for dataset in datasets_response.json().get("datasets", [])
    }
    if VAL15_DATASET_ID not in dataset_ids:
        pytest.skip(f"VAL-15 dataset {VAL15_DATASET_ID} is unavailable.")

    data_root = _data_root()
    checkpoint_root = data_root / "checkpoints" / VAL15_CHECKPOINT
    configuration_path = checkpoint_root / "configuration" / "configuration.json"
    assert (checkpoint_root / ".complete").is_file()
    assert (checkpoint_root / "saved_model.keras").is_file()
    assert (checkpoint_root / "strategy.keras").is_file()
    configuration = json.loads(configuration_path.read_text(encoding="utf-8"))
    training = configuration["training"]
    assert training["dataset_id"] == VAL15_DATASET_ID
    assert training["dynamic_betting_enabled"] is True
    assert training["bet_strategy_model_enabled"] is True
    return VAL15_CHECKPOINT


###############################################################################
def test_learned_strategy_suggestion_applies_without_advancing_pending_step(
    page: Page,
    base_url: str,
    api_context: APIRequestContext,
) -> None:
    checkpoint = _require_val15_fixture(api_context)
    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []
    failed_responses: list[str] = []
    created_session_id: str | None = None
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

    def session_snapshot(session_id: str) -> dict:
        response = api_context.get(f"/api/inference/sessions/{session_id}")
        assert response.status == 200, response.text()
        return response.json()

    def is_session_start(response) -> bool:
        return (
            response.request.method == "POST"
            and response.url.endswith("/api/inference/sessions/start")
        )

    def is_bet_update(response) -> bool:
        return (
            response.request.method == "POST"
            and response.url.endswith(
                f"/api/inference/sessions/{created_session_id}/bet"
            )
        )

    page.set_viewport_size({"width": 1440, "height": 900})
    try:
        page.goto(f"{base_url}/inference")
        page.wait_for_load_state("networkidle")
        page.locator("#inference-checkpoint").select_option(checkpoint)
        page.locator("#inference-dataset").select_option(str(VAL15_DATASET_ID))
        page.locator("#inference-initial-capital").fill("1000")
        page.locator("#inference-bet-amount").fill("10")

        with page.expect_response(is_session_start, timeout=60_000) as start_info:
            page.get_by_role("button", name="Play", exact=True).click()
        start_response = start_info.value
        assert start_response.status == 200, start_response.text()
        start_payload = start_response.json()
        created_session_id = str(start_payload["session_id"])
        prediction = start_payload["prediction"]
        strategy_id = prediction["bet_strategy_id"]
        suggested_bet = prediction["suggested_bet_amount"]
        assert strategy_id in STRATEGY_NAMES
        assert prediction["bet_strategy_name"] == STRATEGY_NAMES[strategy_id]
        assert isinstance(suggested_bet, int) and suggested_bet >= 1

        expect(page.get_by_text(f"Strategy: {STRATEGY_NAMES[strategy_id]}")).to_be_visible()
        expect(page.get_by_text(f"Suggested Bet: € {suggested_bet}")).to_be_visible()
        apply_button = page.get_by_role("button", name="Apply Suggested Bet", exact=True)
        expect(apply_button).to_be_enabled()

        before_snapshot = session_snapshot(created_session_id)
        before_steps = _persisted_steps(created_session_id)
        assert before_snapshot["current_bet"] == 10
        assert before_snapshot["current_capital"] == 1000
        assert before_snapshot["step_count"] == 0
        assert before_snapshot["prediction_pending"] is True
        assert len(before_steps) == 1
        assert before_steps[0][1] == 10
        assert before_steps[0][4:6] == (None, None)

        with page.expect_response(is_bet_update, timeout=30_000) as bet_info:
            apply_button.click()
        bet_response = bet_info.value
        assert bet_response.status == 200, bet_response.text()
        assert bet_response.json()["bet_amount"] == suggested_bet

        after_snapshot = session_snapshot(created_session_id)
        after_steps = _persisted_steps(created_session_id)
        assert after_snapshot["current_bet"] == suggested_bet
        assert after_snapshot["current_capital"] == before_snapshot["current_capital"]
        assert after_snapshot["step_count"] == before_snapshot["step_count"]
        assert after_snapshot["prediction_pending"] is True
        assert len(after_steps) == len(before_steps) == 1
        assert after_steps[0][1] == suggested_bet
        assert after_steps[0][2:] == before_steps[0][2:]
        expect(page.get_by_text(f"€ {suggested_bet}", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()
        page.screenshot(
            path=str(
                Path(__file__).resolve().parents[2]
                / ".."
                / "assets"
                / "QA"
                / "val15-strategy-suggestion.png"
            ),
            full_page=True,
        )
    finally:
        if created_session_id is not None:
            api_context.post(
                f"/api/inference/sessions/{created_session_id}/shutdown"
            )

    assert page_errors == []
    assert console_errors == []
    assert failed_requests == []
    assert failed_responses == []
