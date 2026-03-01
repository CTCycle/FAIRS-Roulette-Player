# Background Job Management

FAIRS uses a centralized job manager for long-running backend work. Training jobs are coordinated by a thread-level manager and executed in a dedicated child process.

## 1. Core components

- `FAIRS/server/services/jobs.py`
  - `JobManager`: tracks jobs, state, progress, and cancellation flags.
  - `job_manager`: singleton used by routes.
- `FAIRS/server/entities/jobs.py`
  - `JobState`: thread-safe mutable state for one job.
  - Response schemas: `JobStartResponse`, `JobStatusResponse`, `JobCancelResponse`.
- `FAIRS/server/learning/training/worker.py`
  - `ProcessWorker`: spawned process wrapper for heavy training workloads.
  - Progress/result channels via multiprocessing queues.

## 2. State model

Each job has:

- `job_id` (8-char UUID fragment)
- `job_type` (for example, `training`)
- `status`: `pending | running | completed | failed | cancelled`
- `progress` (0..100)
- `result` (optional payload)
- `error` (optional error string)
- monotonic timestamps (`created_at`, `completed_at`)

## 3. Execution model

1. Route calls `job_manager.start_job(...)`.
2. `JobManager` creates `JobState`, marks it `running`, and starts a daemon thread.
3. For training, the thread runner (`run_training_job` / `run_resume_training_job`) launches a `ProcessWorker` child process.
4. Worker process emits progress messages (`training_update`) through queue; route layer merges updates into job/result state.
5. Completion updates final status (`completed`, `cancelled`, or `failed`).

## 4. Cancellation semantics

Cancellation is cooperative with escalation:

- API cancellation sets `stop_requested=True` via `job_manager.cancel_job(job_id)`.
- Training route also signals the worker stop event (`worker.stop()`).
- Monitor loop waits for graceful stop; if timeout is exceeded, it terminates the process tree.
- Final job status remains `cancelled` unless a non-cancel failure occurs.

## 5. API integration (current)

Training job endpoints:

- `POST /training/start`
- `POST /training/resume`
- `GET /training/jobs/{job_id}`
- `DELETE /training/jobs/{job_id}`

Live UI polling endpoint:

- `GET /training/status`

The frontend polls status with the server-provided `poll_interval`.

## 6. Pattern for new background jobs

Use this pattern for new long-running work:

```python
job_id = job_manager.start_job(
    job_type="your_job_type",
    runner=run_your_job,
    kwargs={"payload": payload},
)
```

Inside the runner:

- Periodically check `job_manager.should_stop(job_id)` (or a stop event).
- Push progress via `job_manager.update_progress(job_id, progress)`.
- Return a serializable result dict.
- Raise exceptions to mark the job as `failed`.
