"""Live browser coverage for learned inference betting suggestions."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest
from playwright.sync_api import APIRequestContext, Page, expect


VAL15_CHECKPOINT = os.getenv("FAIRS_VAL15_CHECKPOINT", "val15_strategy_20260923")
VAL15_DATASET_ID = 5
STRATEGY_NAMES = {
    0: "Keep",
    1: "Martingale",
    2: "Reverse",
    3: "DAlembert",
    4: "Fibonacci",
}


def _data_root() -> Path:
    configured = os.getenv("FAIRS_DATA_DIR", "").strip()
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2] / "resources"


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
