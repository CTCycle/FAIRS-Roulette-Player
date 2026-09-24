"""Tier 5 VAL-22 repetition, bounded execution, and state-leak coverage."""

from __future__ import annotations

import json
import sqlite3
import time
from uuid import uuid4

from playwright.sync_api import APIRequestContext

from server.common import path as shared_paths
from test_inference_api import (
    get_session_snapshot,
    require_checkpoint,
    require_dataset_id,
    start_inference_session,
)
from test_training_api import (
    VAL08_STORED_CPU_CONFIG,
    VAL10_LONG_STORED_CPU_CONFIG,
    assert_training_idle,
    incomplete_checkpoint_workspaces,
    wait_for_job_completion,
    wait_for_training_running,
    wait_for_training_stopped,
)

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
            step = api_context.post(
                f"/api/inference/sessions/{session_id}/step",
                data={"extraction": 17 + cycle},
            )
            assert step.status == 200, step.text()
            next_prediction = api_context.post(
                f"/api/inference/sessions/{session_id}/next"
            )
            assert next_prediction.status == 200, next_prediction.text()
        finally:
            shutdown = api_context.post(
                f"/api/inference/sessions/{session_id}/shutdown"
            )
            assert shutdown.status == 200, shutdown.text()

        clear = api_context.post(
            f"/api/inference/sessions/{session_id}/rows/clear"
        )
        assert clear.status == 200, clear.text()
        with sqlite3.connect(
            shared_paths.DATABASE_PATH, timeout=5.0
        ) as connection:
            remaining_steps = connection.execute(
                "SELECT COUNT(*) FROM inference_session_steps WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
        assert remaining_steps == 0

        cycle_durations.append(time.perf_counter() - started_at)
        assert _active_sessions() == baseline_sessions
        persisted = _ended_session(session_id)
        assert persisted is not None and persisted[0] is not None
        assert persisted[1] == initial_capital
        assert api_context.get(
            f"/api/inference/sessions/{session_id}"
        ).status == 404

    assert len(set(session_ids)) == 3
    assert api_context.get("/api/training/checkpoints").json() == baseline_checkpoints
    print(
        "VAL22 inference cycles: "
        f"checkpoint={checkpoint}, dataset_id={dataset_id}, session_ids={session_ids}, "
        f"count={len(cycle_durations)}, total={sum(cycle_durations):.3f}s, "
        f"per_cycle={[round(value, 3) for value in cycle_durations]}, "
        f"max={max(cycle_durations):.3f}s, timeout=90s, active_after={_active_sessions()}"
    )

###############################################################################
def test_repeated_settings_writes_remain_parseable_and_leave_no_temp_files(
    api_context: APIRequestContext,
) -> None:
    settings_path = shared_paths.RUNTIME_SETTINGS_FILE
    before_response = api_context.get("/api/settings")
    assert before_response.status == 200, before_response.text()
    before = before_response.json()
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
            assert json.loads(settings_path.read_text(encoding="utf-8"))[
                "jobs"]["polling_interval"] == interval
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
    assert set(settings_path.parent.glob(f".{settings_path.name}.*.tmp")) == set()
    print(
        "VAL22 settings cycles: "
        f"count={len(cycle_durations)}, total={sum(cycle_durations):.3f}s, "
        f"per_cycle={[round(value, 3) for value in cycle_durations]}, "
        f"max={max(cycle_durations):.3f}s, timeout=90s, values={intervals}, "
        f"final_polling_interval={final.json()['jobs']['polling_interval']}, temp_files=0"
    )

###############################################################################
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
