"""Tier 5 VAL-21 malformed-input and fail-closed recovery coverage."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from uuid import uuid4

from playwright.sync_api import APIRequestContext

from server.common import path as shared_paths
from server.services.datasets import MAX_UPLOAD_SIZE_BYTES
from test_inference_api import (
    get_session_snapshot,
    require_checkpoint,
    require_dataset_id,
    start_inference_session,
)
from test_training_api import MINIMAL_TRAINING_CONFIG

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
def test_rejected_settings_patches_preserve_file_and_recover(
    api_context: APIRequestContext,
) -> None:
    before_response = api_context.get("/api/settings")
    assert before_response.status == 200, before_response.text()
    before_settings = before_response.json()
    settings_path = shared_paths.RUNTIME_SETTINGS_FILE
    before_document = settings_path.read_bytes()

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
        assert settings_path.read_bytes() == before_document

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
    assert json.loads(settings_path.read_text(encoding="utf-8"))[
        "jobs"]["polling_interval"] == before_settings["jobs"]["polling_interval"]
    _assert_healthy(api_context)
    print(f"VAL21 settings patches: rejected_statuses={statuses}, recovery=200")

###############################################################################
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
def test_inference_rejections_preserve_live_session_and_recover(
    api_context: APIRequestContext,
) -> None:
    checkpoint = require_checkpoint(api_context)
    dataset_id = require_dataset_id(api_context)
    invalid_checkpoint = api_context.post(
        "/api/inference/sessions/start",
        data={
            "checkpoint": "val21_missing_checkpoint",
            "dataset_id": dataset_id,
            "game_capital": 1000,
            "game_bet": 10,
        },
    )
    assert invalid_checkpoint.status == 404, invalid_checkpoint.text()

    invalid_dataset = api_context.post(
        "/api/inference/sessions/start",
        data={
            "checkpoint": checkpoint,
            "dataset_id": 999999999,
            "game_capital": 1000,
            "game_bet": 10,
        },
    )
    assert invalid_dataset.status == 404, invalid_dataset.text()

    started = start_inference_session(api_context, checkpoint, dataset_id)
    session_id = started["session_id"]
    before_snapshot = get_session_snapshot(api_context, session_id)
    before_rows = _database_rows(
        "SELECT session_id, step_number, bet_amount, predicted_action, "
        "predicted_relative_preference, observed_outcome_id, reward, capital_after "
        "FROM inference_session_steps WHERE session_id = ? ORDER BY step_number",
        (session_id,),
    )
    try:
        invalid_operations = (
            api_context.post(
                f"/api/inference/sessions/{session_id}/step",
                data={"extraction": 37},
            ),
            api_context.post(
                f"/api/inference/sessions/{session_id}/step",
                data={"extraction": "not-a-number"},
            ),
            api_context.post(
                f"/api/inference/sessions/{session_id}/bet",
                data={"bet_amount": 0},
            ),
            api_context.post(
                "/api/inference/sessions/val21_stale_session/step",
                data={"extraction": 17},
            ),
        )
        invalid_statuses: list[int] = []
        for response in invalid_operations:
            _assert_client_error(response)
            invalid_statuses.append(response.status)
            assert get_session_snapshot(api_context, session_id) == before_snapshot
            assert (
                _database_rows(
                    "SELECT session_id, step_number, bet_amount, predicted_action, "
                    "predicted_relative_preference, observed_outcome_id, reward, "
                    "capital_after FROM inference_session_steps "
                    "WHERE session_id = ? ORDER BY step_number",
                    (session_id,),
                )
                == before_rows
            )

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
        f"missing_checkpoint=404, missing_dataset=404, rejected_statuses={invalid_statuses}, "
        f"failed_session_id={session_id}, recovery_session_id={recovery_id}, ended=yes"
    )
