# Tier 3 validation campaign: VAL-11

Date: 2026-09-22
Status: `VAL-11 VALIDATED`; campaign remains `PARTIAL`
Branch: `develop`
Baseline HEAD before the VAL-11 test and QA patch: `fb597eaaeb763cb39d7dae7d7bee36ba1a074b40`

## Scope and boundary

This slice validates the normal single-worker, checkpoint-backed inference lifecycle: start, prediction, manual bet update, observed outcome, next prediction, persisted session history, row clearing, inference-context clearing, and shutdown. Replay/replacement mutations, recovery after backend restart, and strategy-driven bet recommendations remain separate gates in VAL-12 through VAL-15.

The supported profile was Windows, FAIRS `3.4.2`, Python `3.14.7`, Node `22.13.0`, SQLite `3.50.4`, CPU, one Uvicorn worker, API port `8890`, and UI port `8051`.

## Isolated fixture and preserved baseline

The run used copies of `app/resources/database.db`, `runtime-settings.json`, and checkpoint `val00_lineage_20260921` under `%TEMP%\fairs-val11-20260922-fb597ea`. Dataset `5` was `val00_training_lineage` with `120` outcomes. All five checkpoint files matched the repository copy by SHA-256 before and after the run:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `.complete` | 10 | `5963977da4c2cb333a978aa0daa86f36234831cd8bc416443ca9087268bc8645` |
| `configuration/configuration.json` | 890 | `9ec07fa06c5c74d0d69bb31557b6abdc7df36c047c4aebdba01625b23290ce09` |
| `configuration/replay_memory.pkl` | 15,996 | `aac751c1202dc9fd91fc07ecc339b5ac96e628b2b16213612f10490efef89c32` |
| `configuration/session_history.json` | 299 | `54a2aaf0b7824fbb4f670e446ed3c78b2af701e734b93a4d21c25ea33256962b` |
| `saved_model.keras` | 133,738 | `bec2a1837ec6953475d591f9be39465ff45c0423548f6d1c5bc3ea7ac470f18b` |

The repository `.env` has a blank `FAIRS_DATA_DIR` and is loaded with override enabled. The first service attempt therefore ignored the process-level data-root value; it was stopped, its five known validation sessions and four step rows were removed, and all application-table rows were compared with the pre-run clone (no row differences remained). The final run loaded `.env` first and set `FAIRS_DATA_DIR` before ASGI lifespan initialization. The settings file remained byte-identical. The final isolated run left the canonical database with zero inference-session and step rows.

## API lifecycle and storage evidence

The live API suite required the fixed checkpoint and dataset rather than selecting arbitrary fixtures. It covered invalid-session responses, start and prediction snapshots, bet update to `25` without step advancement, observation `17`, reward and capital state, next prediction, row clear, inference-context clear after an uploaded inference dataset, rejection of context clear while a session is active (`409`), and shutdown. Starting a session with the cleared dataset returned `404`.

The live browser/API session produced `Bet on number 21`. Changing the bet to `25` left `Steps 0`; submitting `17` produced reward `-25`, capital `975`, and `Steps 1`. The next prediction appeared as the second row. Stop followed by Clear removed the visible rows and returned the page to its setup state. The browser console contained no warning or error entries. The fixed checkpoint had no suggested-bet amount, so **Apply Suggested Bet** was disabled; only manual bet update is covered here.

After shutdown and row clearing, the isolated SQLite audit found four ended session rows and three retained step rows, with no active sessions. The full-loop session retained the observed outcome `17`, reward `-25`, capital `975`, and its pending next-prediction row. Sessions explicitly cleared by the row-clear flow retained no step rows. This validates persisted history while preserving the product boundary that active model objects are process-local and are not reconstructed after restart or capacity eviction.

## Regression results

| Check | Result |
| --- | --- |
| `app/tests/e2e/test_inference_api.py` against the isolated live API | `10 passed`, no skips (`3.18s`) |
| `app/tests/unit/test_inference_service.py` and `app/tests/unit/test_inference_roulette_settings.py` | `13 passed` (`4.73s`) |
| Ruff on `app/tests/e2e/test_inference_api.py` | passed |
| Live API health and migration state | FAIRS `3.4.2`, status `ok`, SQLite at Alembic head `0002_rename_relative_preference` |
| In-app browser | Prediction, manual bet change, observed result, next prediction, Stop, and Clear visually exercised; zero console warning/error entries |

The in-app browser capture was inspected but no screenshot file was retained. The fixed checkpoint supplied no actionable suggested-bet value. No inference application defect was observed in this slice.

## Closure

VAL-11 is validated for the normal live inference lifecycle on Windows/SQLite/CPU. VAL-12/13 replay and replacement behavior, VAL-14 recovery/restart behavior, and VAL-15 betting strategies remain open. Broader frontend accessibility and visual coverage also remains open; the overall campaign stays `PARTIAL`.
