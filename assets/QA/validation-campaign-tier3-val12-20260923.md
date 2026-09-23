# Tier 3 validation campaign: VAL-12

Date: 2026-09-23
Status: `VAL-12 VALIDATED`; campaign remains `PARTIAL`
Branch: `develop`
Baseline HEAD before this test and QA patch: `2d16d29d0c1818baec2a0c2895af9d496ecd526f`

## Scope and environment

This slice validates inference history replay after correcting an observed result and removing a history row. No runtime, public API, or schema change was needed. Failed-replacement rollback, backend restart recovery, and strategy behavior remain open for later gates.

Profile: Windows `10.0.26200.0`, FAIRS `3.4.2`, Python `3.14.7`, Node `22.13.0`, SQLite `3.50.4`, CPU, one Uvicorn worker, ports `8890` and `8051`. The official Windows launcher started the app; `/api/health` returned `ok`, version `3.4.2`.

Python/E2E commands used `PYTHONPATH=app` and `PLAYWRIGHT_BROWSERS_PATH=runtimes/cache/playwright-browsers`. Focused pytest used repository-local cache/temp directories; the final Windows suite used scratch under `assets/QA/` because data roots under the canonical cache are prohibited.

The backend used isolated copies under `%TEMP%/fairs-val12-20260923-7720` of `database.db`, `runtime-settings.json`, and checkpoint `val00_lineage_20260921`. Dataset `5` was `val00_training_lineage` with `120` outcomes. `settings/.env` temporarily pointed `FAIRS_DATA_DIR` at that root; it was restored byte-for-byte (SHA-256 `a421db30276b690d1ac14549afce9e850af72533b95ebff6fbc2db42610eecde`).

## Browser replay and persisted state

In the in-app browser, initial capital was `1000`, bet `10`, and the first prediction was `Bet on number 21`. Submitting `17` and `18` produced two `-10` results and capital `980`, with a third prediction pending. Correcting step 1 to `21` replaced the live session: step 1 became `+350` / capital `1350`; step 2 remained observed `18`, `-10` / capital `1340`; two steps were confirmed and step 3 was pending. Removing step 2 created another replacement. Final UI: one observed row (`21`), reward `+350`, capital `1350`, `Steps 1`, and a pending second prediction. Capture: [val12-inference-history-replay.png](val12-inference-history-replay.png).

The browser regression reads each replacement snapshot from the live API, compares results/capital/step count/pending state to the UI, asserts `X-Preserve-Inference-Session` carries the prior ID, and verifies the prior session's `/next` returns `404`. Page errors, console errors, failed requests, and HTTP responses >=400 were empty.

## Results

| Check | Result |
| --- | --- |
| Focused browser regression | `1 passed` |
| Inference API plus inference-service unit suites | `20 passed` |
| Ruff on `app/tests/e2e/test_app_flow.py` | passed |
| Standard `cmd /c app\tests\run_tests.bat` | `193 passed, 5 skipped, 3 failed, 55 errors` in `117.23s` |
| Full runner with pytest scratch under `assets/QA/` | `246 passed, 5 skipped, 3 failed, 2 errors` in `118.98s`; VAL-12 regression passed |

The final broad-run failures are outside VAL-12: stored-training checkpoint publication and stop/delete recovery-checkpoint assertions failed; two resume tests could not set up because expected `val10_resume_...` was absent. These remain unresolved and keep the campaign `PARTIAL`. A diagnostic run with pytest temp under `runtimes/cache` hit the app's rule that `FAIRS_DATA_DIR` cannot overlap that disposable cache; moving scratch under `assets/QA/` removed the restart-test errors. Frontend bootstrap passed; frontend unit/E2E phases are skipped because their scripts do not exist.

## Cleanup and remaining gaps

The inference regression shut down and cleared its sessions. Training was idle after the suite. Verified launcher-started process trees were stopped; ports `8051` and `8890` were clear. The original `.env` was restored exactly, and the isolated data root and task-specific pytest scratch were removed. The initial deletion of `runtimes/cache/pytest-tmp/.gitkeep` was preserved.

VAL-12 is validated for correction and row-removal replay on Windows/SQLite/CPU. Failed replacement rollback, restart recovery, and strategy behavior remain open for later gates.
