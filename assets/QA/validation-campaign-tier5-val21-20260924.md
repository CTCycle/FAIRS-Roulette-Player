# Tier 5 VAL-21 malformed-input and recovery campaign

- Date: 2026-09-24
- Status: `VALIDATED`
- Source/test revision: `5f3ac3089810b798d07f1a055a6f8cb1d1754758`
- Develop baseline: `2a93206915c6418347087f22d71ff123df629ef5`

## Acceptance contract

VAL-21 covers malformed and invalid input, failure recovery, fail-closed behavior, and preservation of persisted and process-local state. Rejected input must produce a deterministic 4xx response without a 500, unexpected traceback, partial mutation, or loss of service health. A subsequent valid operation must succeed.

## Environment and isolation

- Windows 11, build `10.0.26200.0`; PowerShell `7.6.6`.
- Project test environment: `app/server/.venv`, Python `3.14.7`; SQLite `3.50.4`; PyTorch `2.10.0+cu130`; one Uvicorn worker.
- Node `22.13.0`, npm `10.9.2`, Chromium through the repository Playwright setup.
- The host's default interpreter reports Python `3.11.15`. Campaign commands explicitly used `app/server/.venv/Scripts/python.exe`, which reports Python `3.14.7`, following the repository's existing Python environment policy; the host default was not used for campaign tests.
- Every live run used a fresh SQLite backup plus copied runtime settings and checkpoint data under `%TEMP%`, with an isolated cache. `settings/.env` was restored byte-for-byte after every runner invocation. Ports `8890` and `8051` were clear after cleanup.
- The deterministic inference lineage was checkpoint `val00_lineage_20260921`, dataset ID `5`.

## Scenarios and results

1. Malformed JSON, missing schema fields, wrong primitive type, and malformed/stale inference session ID were sent through Settings, Training validate/start, and Inference start/step. Responses were `[422, 422, 422, 422, 404]`; `/api/health` returned `200` after every request.
2. Four invalid Settings patches (unknown database field, out-of-range polling interval, wrong interval type, unsupported JIT backend) returned `[422, 422, 422, 422]`. The settings API document and `runtime-settings.json` bytes stayed unchanged. A valid update and reset each returned `200` and restored the original logical document.
3. Malformed and semantically invalid Training validate/start requests returned `[422, 422, 404]`. The status response remained idle with `job_id=None`; dataset rows and published checkpoint file hashes were unchanged; staging was empty. The rejected output name `val21_rejected_0badc3332d` was absent. A subsequent valid `/api/training/validate` request returned `200`, and training status remained idle, proving validation recovery without starting a job.
4. Upload rejection covered unknown dataset kind, invalid delimiter, no valid roulette rows, corrupted XLSX, input one byte above the configured 25 MiB limit, and a filename longer than the 255-character limit. Responses were `[422, 400, 400, 400, 413, 400]`. Dataset records and outcomes matched the before snapshot after each rejection. A valid two-row CSV then uploaded as dataset ID `7`, name `val21_recovery_d04ef593c0`, and was deleted; the original dataset state matched exactly afterward.
5. Invalid checkpoint and dataset starts returned `404`. On a live session using the deterministic lineage, illegal observation values, an illegal bet, and a stale session operation returned `[422, 422, 422, 404]`. The authoritative session snapshot and persisted steps remained identical after each rejection. Valid bet and step operations then succeeded. Failed session `374a05f3501d4a05a0a7af8028583b54` was ended and persisted; recovery session `3ed8389a8e244101a7644df2c43fce49` started with capital `1200`, bet `15`, and zero steps, then ended cleanly.

The settings contract fix rejects `jit_backend` values outside the supported `eager`/`inductor` names before persistence. This closes a defect where a syntactically valid but unsupported backend had been accepted and stored. Existing platform capability validation continues to reject Windows `inductor` while retaining the previous setting.

Existing inference persistence/replacement/capacity rollback and Training preflight regressions also passed in the full suite; no broad exception handling or generic 4xx translation was added.

## Validation evidence

- Focused `test_val21_resilience.py`: `5 passed in 12.32s` on a fresh isolated database at the final source/test revision.
- Complete Windows standard runner on source/test revision `5f3ac3089810b798d07f1a055a6f8cb1d1754758`: `274 passed, 6 skipped in 369.06s`; live-server phase and frontend bootstrap passed. All five VAL-21 tests passed in that run.
- Ruff, frontend lint, production build, generated frontend contract check, and Alembic consistency passed.
- Hosted CI run [35987774300](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/35987774300) completed successfully at this source revision: backend job `107594370768`, frontend job `107594370706`, and PostgreSQL conformance job `107594370370` all passed. Backend validation included Ruff, `171 passed, 1 skipped` unit tests, Alembic consistency, and generated frontend contract check; frontend lint and production build passed; hosted PostgreSQL 17.11 persistence conformance passed. The Ubuntu 24.04 unit job recorded the expected single skip for the Windows-only PowerShell maintenance harness.

The six local pytest skips were the five PostgreSQL tests (no local `TEST_POSTGRES_URL`) and one strategy browser test whose transient checkpoint was not present in the fresh baseline. Hosted PostgreSQL conformance is tracked separately. The standard runner's frontend unit and E2E npm phases remain skipped because those scripts are not defined; `ISSUE-003` remains open.

## Remaining gaps

No remaining VAL-21 acceptance gap was observed. The source-revision hosted CI and PostgreSQL gates are green.
