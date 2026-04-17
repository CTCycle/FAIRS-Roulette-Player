# Background Job Management

Last updated: 2026-04-08

FAIRS uses a centralized in-process job manager for long-running backend work. Training jobs are coordinated by a thread-level manager and execute heavy computation in a dedicated child process.

## 1. Core Components

- `FAIRS/server/services/jobs.py`
  - `JobManager`: tracks jobs, progress, status, results, and cancellation flags.
  - Use dependency construction (`create_job_manager`) and pass `JobManager` explicitly.
- `FAIRS/server/domain/jobs.py`
  - `JobState`: thread-safe mutable state for a single job.
  - API response models: `JobStartResponse`, `JobStatusResponse`, `JobCancelResponse`.
- `FAIRS/server/api/training.py`
  - Training endpoint orchestration and status projections.
  - Training runners: `run_training_job`, `run_resume_training_job`.
- `FAIRS/server/learning/training/worker.py`
  - `ProcessWorker`: child process wrapper for training workloads.

## 2. Job State Model

Each job tracks:

- `job_id` (8-char UUID fragment)
- `job_type` (for example `training`)
- `status`: `pending | running | completed | failed | cancelled`
- `progress` (`0..100`)
- `result` (optional JSON-serializable payload)
- `error` (optional concise error string)
- timestamps (`created_at`, `completed_at`) stored as monotonic values

## 3. Execution Flow

1. API module calls `job_manager.start_job(...)`.
2. `JobManager` creates `JobState`, stores it, marks it `running`, and starts a daemon thread.
3. Training runner starts `ProcessWorker` in a child process.
4. Progress/result updates are merged into job state while worker runs.
5. Final status is set to `completed`, `cancelled`, or `failed`.

## 4. Cancellation Semantics

Cancellation is cooperative with escalation:

- API cancellation sets `stop_requested=True` via `job_manager.cancel_job(job_id)`.
- Training endpoint also signals process stop through `worker.stop()`.
- Monitor loop waits for graceful stop, then force-terminates if timeout is exceeded.
- Terminal state remains `cancelled` unless a separate non-cancel error occurs.

## 5. API Integration (Current)

Training lifecycle endpoints:

- `POST /training/start`
- `POST /training/resume`
- `GET /training/status`
- `POST /training/stop`
- `GET /training/jobs/{job_id}`
- `DELETE /training/jobs/{job_id}`

These endpoints are available under `/api/*`.

## 6. Pattern for New Background Jobs

Use the same orchestration pattern:

```python
job_id = job_manager.start_job(
    job_type="your_job_type",
    runner=run_your_job,
    kwargs={"payload": payload},
)
```

Inside `run_your_job`:

- Check cancellation periodically with `job_manager.should_stop(job_id)` (or equivalent stop event).
- Push progress through `job_manager.update_progress(job_id, progress)`.
- Return serializable dict payload for completion metadata.
- Raise exceptions for deterministic `failed` states.

## 7. Constraints and Recommendations

- Keep heavy CPU/GPU work out of request-handling threads.
- Keep returned `result` payloads compact and API-safe.
- Prefer idempotent cancellation paths to avoid orphaned workers.
- If job state schema changes, update `ARCHITECTURE.md`, tests, and API consumers together.
