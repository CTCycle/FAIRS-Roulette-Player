# Tier 3 validation campaign: VAL-13

Date: 2026-09-23
Status: `VAL-13 VALIDATED`; campaign remains `PARTIAL`
Branch: `develop`
Baseline HEAD before the implementation and QA changes: `80689df24dde3bcb04a300c677bd107117ce9efa`

## Scope and environment

This slice validates rollback when an inference history replacement fails after the candidate session has started. The original live session must retain its state and visible history; the failed candidate is closed while its partial persisted history remains as an audit record. The service and browser regressions passed. The browser regression exposed a stale optimistic edit after the failure, so the UI now reloads the original session snapshot on replay errors. No public API or schema change was made.

Profile: Windows `10.0.26200.0`, FAIRS `3.4.2`, Python `3.14.7`, Node.js `22.13.0`, SQLite `3.50.4`, CPU, one Uvicorn worker, ports `8890` and `8051`. The official Windows launcher started the app; `/api/health` returned `{"status":"ok","application":"FAIRS","version":"3.4.2"}`. The rendered page was inspected in the in-app browser; the regression exercised `/inference` in Playwright Chromium.

The backend used isolated copies under `%TEMP%/fairs-val13-20260923-codex-data` of `database.db`, `runtime-settings.json`, and checkpoint `val00_lineage_20260921`. Dataset `5` was `val00_training_lineage` with `120` outcomes. `settings/.env` temporarily pointed `FAIRS_DATA_DIR` at this isolated root. After validation, the original `.env` was restored byte-for-byte and verified against its pre-run SHA-256 `a421db30276b690d1ac14549afce9e850af72533b95ebff6fbc2db42610eecde`.

## Scenarios and evidence

The service regression starts a live session, injects a persistence failure while registering a replacement, and verifies that the old session remains the only active state entry with an identical snapshot. It also verifies that the candidate database row is deleted, the old session is not ended, and the candidate model is released.

The browser regression starts the fixed checkpoint and dataset, records two outcomes, and leaves the next prediction pending. It begins a correction replacement, lets candidate step 1 persist, and injects `503 Service Unavailable` on candidate step 2. It verifies that:

- The original API snapshot is unchanged and remains usable through a bet update.
- The original persisted session remains open with its original observed steps and pending prediction.
- The candidate rejects further use with `404`, has an `ended_at` value, and retains partial steps `(1, corrected outcome)` and `(2, no outcome)`.
- The visible form and rows return to the original committed values, and remain correct after reload.
- There are no page errors or failed network requests. The sole failed HTTP response and browser console error are the expected injected `503`.

Capture: [val13-inference-replacement-rollback.png](val13-inference-replacement-rollback.png). It shows the restored original values and active Stop control alongside the injected failure message.

## Results

| Check | Result |
| --- | --- |
| Inference service unit suite, including candidate registration rollback | `11 passed` |
| Focused inference service/API and VAL-12/VAL-13 browser regressions | `23 passed` |
| VAL-13 browser regression after audit-preserving teardown change | `1 passed` in `6.43s`; post-teardown SQLite inspection confirmed the closed candidate retained its two partial steps |
| Ruff on `app/tests/unit/test_inference_service.py` and `app/tests/e2e/test_app_flow.py` | passed |
| Frontend lint | passed |
| Frontend production build | passed |
| Standard `cmd /c app\tests\run_tests.bat --basetemp assets\QA\.scratch-val13-standard -o cache_dir=assets\QA\.scratch-val13-standard-cache` | `248 passed, 5 skipped, 3 failed, 2 errors` in `127.82s` |

The standard runner's three failures and two setup errors are the same unrelated training checkpoint publication, stop/delete recovery checkpoint, and resume checkpoint setup cases recorded in the VAL-12 full-run report. In this run the missing checkpoint identifiers were `val08_api_30b45a593f`, `val10_recovery_stop_fe605db3f0`, `val10_recovery_delete_3154af8223`, and `val10_resume_d90c2e0755`. The VAL-13 browser regression passed in the standard run. Compared with the VAL-12 scratch run (`246 passed, 5 skipped, 3 failed, 2 errors`), two additional passing tests include the new regression; there were no new broad-suite failure categories.

The standard runner's live-server and frontend bootstrap phases passed. Frontend unit and E2E phases were skipped because the package does not define those scripts. Five PostgreSQL tests were skipped because `TEST_POSTGRES_URL` was not configured.

## Cleanup and remaining gates

The rollback browser regression shut down its original and candidate sessions. Official launcher option 13 returned `Accesso negato`; after verifying the executable paths and command lines, the exact backend and frontend launcher trees were stopped with targeted `taskkill`. Ports `8051` and `8890` and the targeted PIDs were checked clear. The isolated database/checkpoint copy and repository-local pytest scratch were removed. The original runtime settings file was verified restored exactly.

VAL-13 is validated for failed replacement rollback on Windows/SQLite/CPU. The campaign remains `PARTIAL`; recovery/restart VAL-14 and strategy suggestions VAL-15 remain open, along with later cross-cutting and conditional gates.
