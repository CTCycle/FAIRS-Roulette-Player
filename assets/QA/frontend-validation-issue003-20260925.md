# Frontend Validation Slice and Windows Runner Recheck

- Date: 2026-09-25
- Branch: `develop`
- Base revision: `6e4e7c84dcbd3223494e940424a6662c6954097e`
- Working tree: frontend validation scripts, Windows runner integration, and the restart-test isolation correction described below.

## Scope

Closed ISSUE-003 by adding isolated frontend unit and mocked browser tests, wiring both scripts into the Windows standard runner and frontend CI, and checking the supported desktop width boundary. The current UI specification supports desktop browser viewports at least 1100px wide; phone and mobile-first layouts are outside the supported scope.

The Codex in-app Browser was used first to inspect the rendered Training and Settings pages. The installed Chromium and Microsoft Edge profiles were then checked against the built app. Their screenshots and JUnit reports are retained beside this report.

## Implementation

- Added Vitest unit coverage for Training payload conversion, API response/error parsing, and inference session storage.
- Added Playwright tests with mocked API responses for Training wizard navigation, Inference setup options, Settings save feedback, and the 1100px/1099px minimum-width boundary.
- Added `test:unit` and `test:e2e` to the frontend package, installed and locked Vitest and Playwright, documented the scripts, and added frontend CI steps and artifact retention.
- Integrated browser installation and both scripts into `app/tests/run_tests.bat`. The frontend production build now runs from the client directory so Vite resolves the client root consistently.
- Corrected `test_sqlite_restart_persistence.py` to place app data in a session-scoped operating-system temporary root outside `runtimes/cache`; pytest's configured basetemp remains under the cache by design. This preserves the runtime rule that app data cannot overlap the disposable cache and lets Windows remove SQLite files after restart subprocesses have exited.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| `npm run test:unit` | 11 passed across 3 files | [Vitest output log](frontend-unit-vitest-20260925.log) |
| `npm run test:e2e` — Chromium | 4 passed | [Chromium output log](frontend-e2e-chromium-20260925.log), [`frontend-e2e-junit-chromium.xml`](frontend-e2e-junit-chromium.xml) |
| `npm run test:e2e` — installed Edge | 4 passed | [Edge output log](frontend-e2e-edge-20260925.log), [`frontend-e2e-junit-edge.xml`](frontend-e2e-junit-edge.xml) |
| Desktop width evidence | 1100px supported; 1099px displays the minimum-width notice in both browsers | [Chromium 1100px](frontend-viewport-1100-chromium.png), [Chromium 1099px](frontend-viewport-1099-chromium.png), [Edge 1100px](frontend-viewport-1100-edge.png), [Edge 1099px](frontend-viewport-1099-edge.png) |
| Frontend lint and production build | Passed on the source project | Run from `app/client`; [lint log](frontend-lint-20260925.log) and [build log](frontend-build-20260925.log) record the final rerun. |
| Windows launcher contract tests | 12 passed, including the noninteractive live-service wait regression | [Focused pytest log](frontend-validation-runner-contract-20260925.log) |
| Focused restart persistence regression | 2 passed | Both upload/delete persistence and browser inference-session restart/recovery passed after the temp-root correction. |
| Full Windows standard Python suite | 275 passed, 6 skipped in 392.56s | [`frontend-validation-windows-standard-runner-20260925.log`](frontend-validation-windows-standard-runner-20260925.log) |

The six Python skips were five PostgreSQL tests without `TEST_POSTGRES_URL` and the VAL-15 strategy test without its transient checkpoint fixture. The final full-suite runner invocation explicitly skipped its frontend phases while using a manually prepared isolated preview; the runner-integrated frontend phases were also exercised in an earlier invocation and passed (11 unit tests and 4 Chromium browser tests). The final unit and Chromium/Edge browser scripts were rerun directly against the current source and passed. The temporary mirror's linked `node_modules` caused Vite's build to reject the mirror root; the source-project build from `app/client` and the hosted CI build are the authoritative build checks. In the noninteractive full-run invocation, the old batch `timeout` calls printed localized stdin-redirection errors during the live-service wait even though the phase completed. The runner now uses PowerShell `Start-Sleep`; all 12 focused launcher-contract tests, including the new regression for that wait path, pass.

## Environment and isolation

- Windows 11 build `26200`; Node `22.13.0`; Python `3.14.7`; Playwright `1.63.0`.
- Playwright Chromium `153.0.8010.12` (browser build `1243`) and installed Microsoft Edge `154.0.4258.37`.
- Chromium was installed into a task-owned temporary browser cache for the final rerun, then removed; Edge was already installed.
- The Windows suite used a disposable seeded data copy and isolated test/cache paths. The canonical database SHA-256 remained `F139B42B50E1FF21DC460C8AF90472B83149E5EE1A28B499C77D2438A3136B34`; `settings/.env` remained at SHA-256 `A421DB30276B690D1AC14549AFCE9E850AF72533B95EBFF6FBC2DB42610EECDE`.
- The runner-owned backend and preview processes were stopped. Ports `18890` and `18051` were clear afterward; the configured application ports `8890` and `8051` were not used.

## Gate decisions and remaining limits

- `qa.frontend-test-scripts`: **VALIDATED**. Client unit and mocked desktop browser suites pass in Chromium and Edge; the scripts are wired into the Windows runner and hosted frontend CI.
- ISSUE-003: **CLOSED**. The previously absent frontend script gate is implemented and validated.
- `frontend.workflows` and `validation.campaign`: **PARTIAL** only for audible screen-reader announcement behavior, which the available Browser/UI tools cannot verify. Accessibility structure and keyboard interactions remain covered by existing VAL-16/17 evidence.
- VAL-09 remains **CONDITIONAL**: the ledger/docs record no trigger or acceptance criteria. None were invented for this pass.
- VAL-20 remains **CONDITIONAL**: existing `eager`/`inductor` evidence does not define the complete gate or its acceptance criteria. None were inferred for this pass.
- No validation gate is **BLOCKED**. Next-release checks and packaged distribution remain outside this task; mobile layouts are unsupported by the desktop specification.

Hosted CI and push verification are recorded here after the final commit.
