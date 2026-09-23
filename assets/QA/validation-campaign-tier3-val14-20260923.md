# Tier 3 Validation Campaign — VAL-14 Inference Recovery and Restart

- **Status:** `VALIDATED`
- **Date:** 2026-09-23
- **Tested source revision:** source/test patch based on `91477fc821e95c051fc341198cbf843e6b3cc621` (`develop`)

## Scope and result

VAL-14 verifies inference recovery across a browser reload while the backend remains live, then across a graceful backend restart. The isolated SQLite database retains the ended session and its observed steps. The process-local model session is intentionally not rehydrated: its API lookup returns the expected `404`, the Inference page clears its stale session and returns to setup, and a new session can start and stop successfully.

No product defect or API/schema change was needed. The implementation adds a real-browser regression to `app/tests/e2e/test_sqlite_restart_persistence.py`, using a disposable data root and the fixed checkpoint/dataset lineage.

## Executed scenario

- Created a checkpoint-backed inference session from checkpoint `val00_lineage_20260921` and training dataset `5` in an isolated SQLite data root.
- Recorded a generated nonmatching observed result, advanced to the next prediction, and confirmed the session ID and history were stored by the browser.
- Reloaded the same browser origin while the backend remained live. The browser restored the same session snapshot, prediction state, and history.
- Gracefully stopped and relaunched the backend on the same port with the same isolated data root. The old session request returned `404`.
- Queried SQLite read-only after restart: the old session row remained, was marked ended, and retained the exact pre-restart step history.
- Reloaded the existing browser origin and storage. The rendered Inference page returned to setup, cleared the stale session ID, enabled Play, left Stop disabled, showed no active-session controls, and emitted no page errors or unexpected network errors. The expected session `404` was the only HTTP error recorded.
- Started and stopped a fresh inference session after restart. Both operations succeeded.

Browser capture: [`val14-inference-restart-recovered.png`](val14-inference-restart-recovered.png).

## Validation evidence

| Check | Result |
| --- | --- |
| `app/tests/e2e/test_sqlite_restart_persistence.py` | `2 passed` |
| `app/tests/unit/test_inference_service.py` | `11 passed` |
| Ruff on the changed restart test | Passed |
| Frontend `npm run lint` | Passed |
| Frontend `npm run build` | Passed |
| Standard `app/tests/run_tests.bat` with repository-local scratch/cache and isolated data root | `254 passed, 5 skipped`; exit code `0` |

The five Python skips are PostgreSQL conformance tests because `TEST_POSTGRES_URL` was not configured. The standard runner also reports frontend unit and frontend E2E phases as `SKIPPED` because the frontend package has no corresponding npm scripts. During service startup, the runner emitted a nonfatal Windows input-redirection timeout message in its readiness retry loop; health checks subsequently passed and the runner completed successfully.

## Environment and cleanup

Windows `10.0.26200.0`; Python `3.14.7`; Node `22.13.0`; SQLite `3.50.4`; Playwright `1.60.0` with the repository-vended Chromium; CPU; one backend worker. The isolated browser regression used API port `63399` and UI port `63400`; the standard runner used its configured ports `8890` and `8051`.

Test data, backend/frontend logs, and writable scratch/cache contents were isolated under `assets/QA/` and removed after validation. Nineteen empty pytest scratch directories remain because Windows denied deletion; their ACLs were not changed. The standard runner left its backend and Vite preview process trees listening on `8890` and `8051`; process command lines and start times tied them to this run, so those trees were stopped and the configured ports were checked clear. The standard runner's shared-data clone was isolated. `settings/.env` was not modified and its SHA-256 remained `A421DB30276B690D1AC14549AFCE9E850AF72533B95EBFF6FBC2DB42610EECDE`. Ports `8051`, `8890`, `63399`, and `63400` had no listeners after cleanup.

## Gate state and next action

VAL-14 is `VALIDATED` for the supported Windows/SQLite/CPU profile. The campaign remains `PARTIAL`: proceed to VAL-15 strategy suggestions while preserving the same checkpoint and dataset lineage. PostgreSQL conformance and standalone frontend test scripts remain separate open gates.
