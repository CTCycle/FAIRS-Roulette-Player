# Validation evidence: VAL-02 through VAL-04

Validated 2026-09-22 on `develop`, application version `3.4.2`.

Canonical ledger: [`project_status_ledger.md`](../docs/project_status_ledger.md). History consulted: [`validation-campaign-tier0-20260921.md`](validation-campaign-tier0-20260921.md), [`launcher-state-validation-20260921.md`](launcher-state-validation-20260921.md), and [`python314-migration-validation-20260921.md`](python314-migration-validation-20260921.md), along with the settings, UI, API, and testing documents indexed from `assets/docs/project_index.md`.

## Tested revision and environment

- Application source revision: `af1a584d4e6de0c87bed03dde9430a32890e67d5`.
- A one-line implementation fix was applied in `app/server/api/settings.py` after the first regression run exposed a deprecated HTTP 422 constant. The final implementation-file SHA-256 is `52A4E0474CAE18B4BDAF3FC8E17D951C952EE1BAEEB4091A14D22AF01E36D346`. Two validation-only browser regression tests were added and included in the final run; their SHA-256 values are `CBC021987433FBEA42A7310CC90CA2B1C451AE362B8931719B08FE7E45364719` (`app/tests/e2e/test_app_flow.py`) and `D20E2EDC4E279F1E536C54A0BEDE2FDA1BB7E1C798CFF578D62EDB38271E67DC` (`app/tests/e2e/test_settings.py`).
- Windows 11 `10.0.26200`, managed Python `3.14.7`, SQLite `3.50.4`, PyTorch `2.10.0+cu130`, CPU, one backend worker.
- Started through `start_on_windows.ps1`, option 1. Frontend `127.0.0.1:8051`, backend `127.0.0.1:8890`; `/api/health` returned `ok`, `FAIRS`, `3.4.2`.
- The launcher used disposable data root `assets/QA/.val02-04-runtime`. Its runtime settings were the defaults before testing and were the same defaults afterward (SHA-256 `01166A7AE72EB39894DC416A9177D802549AD642C73051559B0F0C2042767433`). No dataset, checkpoint, training job, or inference session was created in this pass.
- VAL-00 training lineage was not needed for these slices. The minimum VAL-01 prerequisite was rechecked with the current official launcher, healthy backend, and visible frontend route.

## VAL-02 — routing and desktop layout

**Previous status:** `PARTIAL`; the campaign map identified layout and below-minimum desktop behavior as incomplete. The current implementation defines `/training`, `/inference`, and `/settings`, a 1100px main-layout minimum with a narrower-window notice, and a two-column inference workspace.

**Inspected files:** `app/client/src/App.tsx`, `app/client/src/components/MainLayout.tsx`, `MainLayout.css`, `app/client/src/pages/Inference/GameSession.tsx`, and `GameSession.module.css`.

**Executed:** the official launcher served the real frontend and backend. The in-app browser visibly rendered Training and Inference; the Training route was inspected at 1100px and the narrower Inference view at 1098px. A Playwright regression test asserted the exact 1100px supported boundary and 1099px below-minimum boundary, including the notice, retained 1100px shell, two inference columns, and aligned panels. It also asserted no page errors, console errors, failed requests, or HTTP error responses. Existing home, navigation, training, and inference page flows ran as part of the regression set.

**Result:** `VALIDATED`. Eight focused browser tests passed (the boundary test plus seven route/page tests). No functional defect was reproduced. The empty checkpoint and dataset selectors reflected the fresh disposable runtime state.

**Evidence note:** visual screenshots were captured and inspected through the Codex in-app browser during the run. Playwright's file screenshot call failed with `Page.captureScreenshot: Unable to capture screenshot`; the layout assertions were separated from that capture call and passed at the exact requested widths. The visual captures remain in the task's browser output rather than as PNG files under `assets/QA/`.

## VAL-03 — HTTP and generated API contracts

**Previous status:** the API-contract component was `VALIDATED`; VAL-03 was listed as a conditional/low-cost gate for rechecking generated contracts and route schemas.

**Inspected files:** `app/server/api/`, `app/server/contracts/`, `app/scripts/generate_frontend_contracts.py`, `app/scripts/export_openapi.py`, and `app/client/src/generated/api.ts`.

**Executed:** live `/api/health` and `/openapi.json` requests against the launched application; generated frontend contract check; `test_generated_contracts.py` and `test_architecture_cleanup.py`.

**Result:** `VALIDATED`. Health reported application/version `FAIRS`/`3.4.2`; live OpenAPI reported 24 paths and 42 schemas, including health, settings, training, upload, and inference contracts. The generated TypeScript contract was current, and the two targeted test files passed (3 tests).

**Invocation diagnosis:** direct file execution of `app/scripts/generate_frontend_contracts.py --check` failed because the `scripts` package was not on `sys.path`. Running it as a module from `app/` (`python -m scripts.generate_frontend_contracts --check`) passed. This was an invocation-context issue; no contract defect or source fix was needed.

## VAL-04 — runtime settings

**Previous status:** `VALIDATED` in the runtime-settings component evidence dated 2026-09-21.

**Inspected files:** `app/client/src/pages/Settings/SettingsPage.tsx`, `app/client/src/utils/settingsApi.ts`, `app/server/api/settings.py`, `app/server/services/settings.py`, `app/server/contracts/settings.py`, and runtime capability/configuration modules.

**Executed:** the browser Settings flow loaded defaults, saved roulette values and reloaded them, saved polling interval and reloaded it, enabled JIT with the supported `eager` backend and reloaded it, reset all settings, opened/dismissed Help, and navigated between Settings and Training. A second browser scenario submitted a reversed number range and an empty roulette pool; both showed the expected visible validation message, sent no PATCH request, and reloaded the unchanged defaults. Settings API, service, capability, system, and roulette-runtime tests ran. A direct CPU `torch.compile(..., backend="eager")` smoke returned `[2, 3, 4]` on PyTorch `2.10.0+cu130`.

**Result:** `VALIDATED`. Both Settings browser tests passed. The settings API/unit selection passed 39 tests, covering partial updates, reload/reset, strict rejection, supported JIT, Windows `inductor` rejection, live-service propagation, and rollback after injected propagation failure. Runtime settings on disk and through the live GET endpoint were defaults after the run; no user settings or data were modified.

**Issue and fix:** the first combined run emitted an AnyIO deprecation warning for `HTTP_422_UNPROCESSABLE_ENTITY` on the Windows JIT rejection path. `app/server/api/settings.py` now uses the recommended `HTTP_422_UNPROCESSABLE_CONTENT` constant, which resolves to the same 422 status. The exact settings API test and adjacent settings tests passed afterward, and the warning disappeared from the final combined run.

**Observed diagnostics:** the final disposable log contains one backend `ERROR` trace from the intentional `RuntimeError("simulated propagation failure")` in `test_propagation_failure_restores_persisted_and_training_state`; the rollback test passed. This was a test-injected rollback case, not a live Settings failure.

## Combined regression and cleanup

Final focused regression command covered the desktop boundary, home/navigation/training/inference routes, generated contracts, architecture cleanup, both Settings browser scenarios, settings API, settings system/service, runtime capability, and roulette runtime settings after the fix: **52 passed, no warnings, 22.31s**. Before the fix, the same selection passed 52 tests with the deprecation warning described above. The standalone generator check and direct JIT smoke also passed on the fixed source.

The initial Playwright screenshot failure was not counted as an application behavior failure. The launcher option 13 stopped all nine repository-owned FAIRS processes; ports `8051` and `8890` were clear afterward. The temporary data, pytest cache, and basetemp directories were removed. `settings/.env` was restored byte-for-byte to its original 1245-byte content (SHA-256 `A421DB30276B690D1AC14549AFCE9E850AF72533B95EBFF6FBC2DB42610EECDE`). The pre-existing ACL-restricted `app/tests/.pytest-tmp/full-suite` tree produced Git scan warnings and was left untouched. No VAL-05 or later slice was executed.
