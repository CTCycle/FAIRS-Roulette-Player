# Tier 2 validation campaign: VAL-10

Date: 2026-09-22
Status: `VAL-10 VALIDATED`; campaign remains `PARTIAL`
Branch: `develop`
Baseline HEAD before this test and documentation patch: `25a00bd2e4bc3378f089c4c815fd532c1a371fc5`

## Scope and boundary

This slice validates deterministic cancellation and concurrency, cancellation during checkpoint resume, successful resume lineage and validation-metric provenance, and the Training-to-Inference checkpoint handoff. The validation prediction loop remains in VAL-11. No backend runtime implementation changes were required; the source changes add strict API, unit, and browser regressions for the existing behavior.

The supported profile was Windows, FAIRS `3.4.2`, Python `3.14.7`, Node `22.13.0`, SQLite `3.50.4`, CPU, one Uvicorn worker, and ports `8890` (API) and `8051` (UI). The application database was `app/resources/database.db`; Alembic was at `0002_rename_relative_preference` (head). The backend health endpoint returned `{"status":"ok","application":"FAIRS","version":"3.4.2"}`.

The official Windows launcher was attempted first, but could not read the managed runtime's `runtimes/python/python314._pth` (`Access denied`). Validation therefore used the repository Python environment to start the backend directly with `--workers 1`, then checked live API health and state. The launcher failure is an environment permission boundary, not a VAL-10 application failure.

## Preserved VAL-00 baseline

- Dataset `5` remained `val00_training_lineage`, with `120` rows.
- The only published checkpoint after cleanup was `val00_lineage_20260921`.
- Training was idle before and after the campaign; the final status had `is_training=false` and `job_id=null`.
- The protected checkpoint's complete file-signature set was unchanged:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `.complete` | 10 | `5963977da4c2cb333a978aa0daa86f36234831cd8bc416443ca9087268bc8645` |
| `configuration/configuration.json` | 890 | `9ec07fa06c5c74d0d69bb31557b6abdc7df36c047c4aebdba01625b23290ce09` |
| `configuration/replay_memory.pkl` | 15,996 | `aac751c1202dc9fd91fc07ecc339b5ac96e628b2b16213612f10490efef89c32` |
| `configuration/session_history.json` | 299 | `54a2aaf0b7824fbb4f670e446ed3c78b2af701e734b93a4d21c25ea33256962b` |
| `saved_model.keras` | 133,738 | `bec2a1837ec6953475d591f9be39465ff45c0423548f6d1c5bc3ea7ac470f18b` |

## Cancellation and concurrency

A deliberately long stored-dataset CPU run used dataset 5, 20 episodes, and 1,000 maximum steps. Manual live job `1beac06b` was observed active with `is_training=true` before the concurrency probes:

| Probe | Result |
| --- | --- |
| Second `POST /api/training/start` while active | `409`, training already in progress |
| `POST /api/training/resume` while active | `409`, training already in progress |
| `POST /api/training/stop` | `200`, stop requested; target job ended specifically `cancelled` |
| Post-cancellation global status | Idle, no active job |
| Checkpoint/staging state | No checkpoint published for the cancelled run; no incomplete staging workspace remained |

The API regression now uses the same long-running shape and contains no skip path for a run that completes too quickly. The concurrency case verifies the exact active job ID before issuing either rejection. A parameterized cleanup regression exercises both `/api/training/stop` and `DELETE /api/training/jobs/{job_id}`; each requires terminal status `cancelled`, idle global status, absent output/staging data, and then starts and completes a fresh short run successfully.

## Resume and checkpoint publication boundary

The test fixture creates a unique disposable real checkpoint from dataset 5 with a validation split. The resume-cancellation regression starts a 20-episode continuation, confirms the exact resume job is active and a resume workspace exists, then cancels it. The job must finish as `cancelled`; the published checkpoint metadata and every file hash must match the pre-resume snapshot, and no staging workspace may remain.

The successful-resume regression resumes the same one-episode fixture for exactly two additional episodes. It verifies the returned job ID through active and terminal status, restored history, total episodes `3`, preserved original configuration and `dataset_id=5`, appended episodes, finite final loss/RMSE, and published checkpoint files/configuration. It also checks that finite validation loss/RMSE samples exist on newly appended episodes, then requires the checkpoint's final validation metrics to equal those resumed-run samples. This prevents stale validation measurements from satisfying the assertion.

## Training UI provenance handoff

Using the real Training page in Codex's in-app browser, the baseline checkpoint's **Open checkpoint in Inference** action navigated to `/inference` with:

| Provenance value | Observed Inference selection |
| --- | --- |
| Checkpoint | `val00_lineage_20260921` |
| Dataset | `val00_training_lineage` (ID `5`) |
| Initial capital | `1000` |
| Bet amount | `10` |

The browser regressions assert the same values and capture page, console, and request errors. A second browser test supplies incompatible checkpoint provenance (`dataset_id=999999`) and verifies the Training preview reports the need for an explicit dataset choice instead of silently selecting a different dataset. No prediction was executed.

## Regression results

| Check | Result |
| --- | --- |
| `app/tests/e2e/test_training_api.py` | `29 passed` (all tests, no VAL-10 cancellation/resume skips) |
| Strengthened fresh-validation resume case after its final assertion change | `1 passed, 28 deselected` |
| `app/tests/unit/test_training_service.py` and checkpoint service tests | `20 passed` |
| `app/tests/e2e/test_app_flow.py` | `20 passed`, including both checkpoint-handoff cases |
| Ruff on the three changed Python test files | passed |
| `npm run lint` | passed |
| `npm run build` | passed; TypeScript/Vite cache paths were temporarily redirected to `%TEMP%` after the protected canonical cache returned `EPERM`, and those temporary config edits were reverted |
| Broad `app/tests/unit` plus `app/tests/e2e` regression | `246 passed, 8 skipped, 1 failed` |
| Broad regression excluding `app/tests/e2e/test_settings.py` | `245 passed, 8 skipped` |

The single broad-suite failure was `TestSettingsPage.test_settings_edit_reload_reset_and_navigation[chromium]`. It reproduced when `test_settings.py` was run alone: the Settings save received HTTP 500 because Windows returned `WinError 5` from `os.replace` while replacing `app/resources/runtime-settings.json`. This host ACL failure is outside VAL-10; no Settings implementation change was made. The eight skips are conditional environment/fixture cases. The broad regression preceded the final strengthened assertion; the successful-resume scenario was rerun afterward and passed with the added fresh-validation checks.

## Cleanup and closure

The fixture deleted only its uniquely named VAL-10 checkpoint. Final checks found dataset 5 unchanged, `val00_lineage_20260921` as the only published checkpoint, the protected checkpoint hashes unchanged, Alembic at `0002_rename_relative_preference`, and training idle. VAL-10 is validated for the supported Windows/SQLite/CPU profile. The next campaign slice is VAL-11 live inference; `backend.training` can be promoted to `VALIDATED`, while the overall campaign remains `PARTIAL`.
