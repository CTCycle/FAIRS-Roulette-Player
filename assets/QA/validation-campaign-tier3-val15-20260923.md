# Tier 3 Validation Campaign — VAL-15 Strategy Suggestions

- **Status:** `VALIDATED`
- **Date:** 2026-09-23
- **Tested source revision:** working-tree source/test patch based on `5cd0b70105b553a13888fd308bc2a35e9070164f` (`develop`)

## Scope and result

VAL-15 validates model-selected strategy output, the visible suggested bet, and applying that suggestion while an inference prediction is pending. The browser flow used a newly trained strategy checkpoint from stored dataset 5. Applying the suggestion updated the current bet and the same pending history row; it did not advance the step or change capital, prediction, or outcome history.

No public API or schema change was needed. A real Training run exposed that spawned workers did not bootstrap the configured runtime paths, so their checkpoint repository fell back to `app/resources`. Worker startup now calls the shared runtime bootstrap before running its target, and a focused unit regression protects that boundary. The standard runner also exposed a test cleanup race: the minimal training test requested stop but did not require its job to reach a terminal state. The test now waits for that job and verifies the manager is idle before returning.

## Training run

- Started from the supported Training wizard using dataset ID `5`, `val00_training_lineage` (120 rows), stored-data mode, CPU, one episode, 100 steps, perceptive field 8, batch size 100, replay buffer 100, and max memory 100.
- Enabled dynamic betting and the five-action strategy model. The run used no GPU or mixed precision.
- Training job `b8ba00d1` completed and published checkpoint `val15_strategy_20260923` under the isolated `FAIRS_DATA_DIR`. The checkpoint contains `.complete`, `saved_model.keras`, `strategy.keras`, and `configuration/configuration.json`; the persisted configuration records dataset 5 and both betting flags as enabled.
- Final training metrics were loss `1.7523360252` and RMSE `1.3237582445`.

The first training attempt (job `83df2627`) revealed the worker-path defect and wrote its task-created checkpoint under `app/resources`. That checkpoint was moved into the isolated QA scratch area and removed during cleanup. The canonical SQLite database remained unchanged; its SHA-256 matched the pre-run value `F510C96336FE1ACE67AC7C7FE45F5F083A75C28A3D24C1E1D64BFB16E54D4EB6` after the application was stopped.

## Browser regression

`app/tests/e2e/test_inference_strategy.py` selected checkpoint `val15_strategy_20260923` and dataset 5, then started a real inference session with capital `1000` and bet `10`. The page visibly showed `Bet on High (19-36)`, strategy `DAlembert`, and suggested bet `€ 10`.

The test captured the session snapshot and SQLite step row before and after applying the suggestion. Before and after, capital remained `1000`, step count remained `0`, the prediction stayed pending, and there was exactly one unobserved step. Applying the suggestion set the current bet and pending row amount to `10`; the prediction, preference, outcome, reward, and capital fields remained unchanged. The start and bet-update requests returned `200`. Page errors, console errors, failed requests, and unexpected HTTP responses were all absent.

Browser capture: [`val15-strategy-suggestion.png`](val15-strategy-suggestion.png).

## Validation evidence

| Check | Result |
| --- | --- |
| Strategy-model unit and worker-bootstrap unit coverage (`test_fallback.py`, `test_training_service.py`) | `18 passed` |
| VAL-15 real-checkpoint browser regression | `1 passed` |
| Training startup/cancellation cleanup regression | `3 passed` |
| Standard Windows runner (`app/tests/run_tests.bat`) | `257 passed, 5 skipped`; exit code `0` |
| Ruff on changed Python files | Passed |
| Frontend `npm run lint` | Passed |
| Frontend `npm run build` | Passed |

The five standard-runner skips are PostgreSQL contract tests because `TEST_POSTGRES_URL` was not configured. The runner reports frontend unit and E2E phases as `SKIPPED` because `app/client/package.json` has no such scripts. These remain separate validation gates.

## Environment and cleanup

Windows `10.0.26200.0`; Python `3.14.7`; Node `22.13.0`; SQLite `3.50.4`; Playwright `1.60.0` with repository Chromium; CPU; one backend worker. The official launcher and standard runner used isolated ports `63399` and `63400` and the QA scratch data root under `assets/QA/.scratch-val15-20260923/`.

After recording the evidence, the task-owned checkpoint/data scratch root was removed, the official launcher backend and frontend process trees were stopped by verified command identity, and ports `63399` and `63400` were confirmed clear. `settings/.env` was restored byte-for-byte; its SHA-256 is `A421DB30276B690D1AC14549AFCE9E850AF72533B95EBFF6FBC2DB42610EECDE`.

## Gate state and next action

VAL-15 is `VALIDATED` for the supported Windows/SQLite/CPU profile. `backend.training` and `backend.inference` remain `VALIDATED`; the overall campaign remains `PARTIAL`. Continue with VAL-16. PostgreSQL conformance and standalone frontend test scripts remain separate open gates.
