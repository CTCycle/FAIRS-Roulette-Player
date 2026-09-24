# Tier 5 VAL-22 repetition, bounds, and state-leak campaign

- Date: 2026-09-24
- Status: `VALIDATED`
- Source/test revision: `5f3ac3089810b798d07f1a055a6f8cb1d1754758`
- Develop baseline: `2a93206915c6418347087f22d71ff123df629ef5`

## Acceptance contract

VAL-22 covers repetition and soak behavior, bounded execution and state, cleanup, and state-leak detection. Repeated lifecycles must return to their defined clean baseline, capacity/history bounds must hold, and each scenario must finish within the repository's existing operational timeouts. No machine-specific microbenchmark threshold was introduced.

## Environment and isolation

- Windows 11, build `10.0.26200.0`; PowerShell `7.6.6`.
- Project test environment: `app/server/.venv`, Python `3.14.7`; SQLite `3.50.4`; PyTorch `2.10.0+cu130`; one Uvicorn worker.
- Node `22.13.0`, npm `10.9.2`, Chromium through the repository Playwright setup.
- The host's default interpreter reports Python `3.11.15`. Campaign commands explicitly used `app/server/.venv/Scripts/python.exe`, which reports Python `3.14.7`, following the repository's existing Python environment policy; the host default was not used for campaign tests.
- Live runs used fresh SQLite backups plus copied runtime settings and checkpoint data under `%TEMP%`, with an isolated cache. `settings/.env` was restored byte-for-byte. Ports `8890` and `8051` were clear after the full runner.
- Inference cycles used checkpoint `val00_lineage_20260921`, dataset ID `5`.

## Scenarios and results

1. **Application lifespan:** four entry/exit cycles reached `ready` then `stopped`. Each cycle created fresh database, training manager/service, and inference service objects; database disposal and training/inference shutdown each occurred exactly once per cycle.
2. **Inference repetition and mutation:** three `start → bet → step → next → shutdown → clear` cycles used session IDs `31cbf6b07fc948ae93d2d52c932e7f25`, `a8c21fe96d0e4ecda15ab81c87f438f2`, and `6a7b8962f9914d37b4943d46a0334a4c`. Every new session started with its requested capital/bet and zero steps. After each cycle, no session was live, the persisted row was ended, its step rows were cleared, the stale live-session route returned `404`, and the checkpoint list matched baseline.
3. **Inference capacity:** the service was driven through 18 session starts with `max_sessions=16`. The live collection never exceeded 16; the two oldest sessions were ended and evicted in order; their model/strategy/context references were released. Shutdown cleared the remaining sessions and references. The existing eviction-persistence failure regression also passed and retained the prior valid session.
4. **Training cancellation and recovery:** three cycles each performed `start → running → cancel → cancelled/idle → recovery run → completed/idle`. Cancelled job IDs were `5d83cac0`, `0a7b2144`, and `c7b8cf2d`; recovery job IDs were `56e11ce4`, `cda309ff`, and `3128b0aa`. Cancellation checkpoints `val22_cancel_59b89fa78f`, `val22_cancel_905bd12e25`, and `val22_cancel_eb4f3acf78` were not published; each staging workspace was absent. Recovery checkpoints `val22_recovery_155dd4253e`, `val22_recovery_dfc92aa775`, and `val22_recovery_cfdbd181c9` completed and were deleted. Total cycle time was `30.229s`, per-cycle `[10.246, 10.245, 9.739]s`, maximum `10.246s`; existing cancellation and recovery timeouts were 45s and 90s. Final active-training status was `False`.
5. **Training telemetry bound:** 2,001 updates retained exactly 2,000 history points. Oldest retained step was `2`; newest was `2001`.
6. **TrainingRunManager cleanup:** four terminal jobs were created and cleaned. Dead thread references and stopped worker references were released, active-run detection returned false, and repeated shutdown remained idempotent. The retained latest-run status projection remained available.
7. **Settings repetition:** ten save/read cycles persisted bounded polling intervals `[0.5, 0.75, 1.0, 1.25, 1.5, 0.5, 0.75, 1.0, 1.25, 1.5]`. Total was `0.205s`, per-cycle `[0.021, 0.021, 0.021, 0.021, 0.020, 0.020, 0.020, 0.020, 0.020, 0.019]s`, maximum `0.021s`, below the existing 90s operational bound. Final settings equaled the original document; it remained parseable and no temporary file remained.

The manager cleanup regression exposed that the most recent terminal job retained a dead thread reference and stopped worker reference. `_prune_terminal_runs_locked` now releases these references for every terminal run while retaining the latest completed run projection. The repeated unit regressions pass.

## Structural leak audit

- Focused VAL-22 started with zero active persisted inference sessions, idle training state, and a baseline checkpoint list. After each inference cycle the active-session set returned to empty; after the training cycles the checkpoint list and staging-directory set matched baseline and training was idle.
- All disposable recovery checkpoints and the VAL-21 recovery dataset were removed. The ten settings writes left no temporary settings files.
- After the final complete runner, the isolated database had zero active inference sessions, zero `val21_*`/`val22_*` datasets, and no checkpoint staging/backup/publish directories. No runner, pytest, Uvicorn, or Vite process or listener remained.
- The final runner's pre-run checkpoint snapshot and canonical `app/resources/checkpoints` contained the same 86 files with identical per-file SHA-256 values. The canonical database SHA-256 remained `dba6cc0af5d07f9a148dcbe016fdb96773722170913e704e93c19c06e323b4cd`; runtime settings SHA-256 remained `01166a7ae72eb39894dc416a9177d802549ad642c73051559b0f0c2042767433`.

## Validation evidence

- Focused `test_val22_resilience.py`: `3 passed in 32.97s` on a fresh isolated database at `2ab95bea56d29ec4baf0b71e21436c464e012c40`; the VAL-22 files were unchanged afterward and all three passed again in the final standard runner at this report's source revision.
- Capacity, telemetry-bound, four-cycle lifespan, and manager cleanup unit regressions passed in the complete suite.
- Complete Windows standard runner on source/test revision `5f3ac3089810b798d07f1a055a6f8cb1d1754758`: `274 passed, 6 skipped in 369.06s`; live-server phase and frontend bootstrap passed. All three VAL-22 tests passed in that run.
- Ruff, frontend lint, production build, generated frontend contract check, and Alembic consistency passed.
- Hosted CI run [35987774300](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/35987774300) completed successfully at this source revision: backend job `107594370768`, frontend job `107594370706`, and PostgreSQL conformance job `107594370370` all passed. Backend validation included Ruff, `171 passed, 1 skipped` unit tests, Alembic consistency, and generated frontend contract check; frontend lint and production build passed; hosted PostgreSQL 17.11 persistence conformance passed. The Ubuntu 24.04 unit job recorded the expected single skip for the Windows-only PowerShell maintenance harness.

The six local pytest skips were the five PostgreSQL tests (no local `TEST_POSTGRES_URL`) and one strategy browser test whose transient checkpoint was not present in the fresh baseline. Hosted PostgreSQL conformance is tracked separately. The standard runner's frontend unit and E2E npm phases remain skipped because those scripts are not defined; `ISSUE-003` remains open.

## Remaining gaps

No remaining VAL-22 acceptance gap was observed. The source-revision hosted CI and PostgreSQL gates are green.
