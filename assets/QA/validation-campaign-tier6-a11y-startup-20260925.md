# Tier 6 Accessibility and Startup Follow-up

- Date: 2026-09-25
- Branch: `develop`
- Tested revision: `c482709884fe05d81c1d7a4e459861d986916c4a`
- Scope: Revisit the remaining `frontend.workflows` and `validation.campaign` debt, recheck the live Settings feedback states, and repeat the official Windows launcher boundary.

## Gate disposition

| Gate | Final status | Current result |
| --- | --- | --- |
| `frontend.workflows` | `PARTIAL` | Live desktop save, reset, validation-error, recovery, and persisted reload states are current and accessible in the browser tree. Audible Narrator output was not observable. |
| `validation.campaign` | `PARTIAL` | Client unit/E2E/lint/build checks and live desktop feedback passed. The audible announcement sub-check remains incomplete. |
| `qa.frontend-test-scripts` | `VALIDATED` | Current dependency tree passed 11 Vitest tests and 4 mocked Chromium cases; lint and production build also passed. |
| `application.startup` | `VALIDATED` with a host setup limitation | The supported warm/standard path remains covered by the existing current-tree evidence. A fresh official launcher attempt on this host stopped in `npm ci` because protected canonical-cache entries returned `EACCES`; an isolated cache recovered the dependency install and allowed the live browser check. |

## Live rendered workflow

The official launcher was attempted first. After its cache-bound npm failure, the already prepared frontend was served on the configured UI port and the backend was started with the supported single-worker command against a disposable data root. `GET /api/health` returned `200` with `{"status":"ok","application":"FAIRS","version":"3.4.2"}`. The canonical `settings/.env` and SQLite database hashes remained `A421DB30276B690D1AC14549AFCE9E850AF72533B95EBFF6FBC2DB42610EECDE` and `F139B42B50E1FF21DC460C8AF90472B83149E5EE1A28B499C77D2438A3136B34`.

In the Codex in-app browser, the default viewport correctly showed the documented minimum-width notice. In Chrome at the supported desktop width, the live Settings page rendered without the notice. The following states were exercised against the disposable backend/data root:

1. Changed Minimum from `0` to `1` and saved. The accessibility tree exposed `Settings saved.` and the value remained `1` after reload.
2. Reset to defaults. The accessibility tree exposed `Settings reset to defaults.` and Minimum returned to `0`.
3. Entered invalid Minimum `37` and submitted. The live page exposed the validation error `Il valore deve essere inferiore o uguale a 36.`; the current source retains `role="alert"` for the error surface and `aria-invalid`/`aria-describedby` on the field.
4. Corrected the value to `1` and saved. The error disappeared, the `Settings saved.` feedback returned, and the Save button became disabled once the draft matched persisted settings.

The final rebuilt page was also visually inspected. The Settings navigation, form grouping, feedback banner, inputs, and action buttons remained legible and aligned at desktop width. No product defect was reproduced in these flows.

## Automated current-tree checks

| Check | Result | Evidence |
| --- | --- | --- |
| Vitest unit suite | `11 passed` across 3 files | [`frontend-a11y-unit-20260925.log`](frontend-a11y-unit-20260925.log) |
| Mocked Chromium browser suite | `4 passed` in `5.7s` | [`frontend-a11y-e2e-20260925-final.log`](frontend-a11y-e2e-20260925-final.log), [`frontend-e2e-junit-chromium.xml`](frontend-e2e-junit-chromium.xml) |
| Frontend lint | Passed | [`frontend-a11y-lint-20260925.log`](frontend-a11y-lint-20260925.log) |
| Production build | Passed: TypeScript plus Vite, `1771` modules transformed | [`frontend-a11y-build-20260925.log`](frontend-a11y-build-20260925.log) |
| Desktop boundary | Existing current Chromium captures refreshed: `1100px` supported and `1099px` shows the documented notice | [`frontend-viewport-1100-chromium.png`](frontend-viewport-1100-chromium.png), [`frontend-viewport-1099-chromium.png`](frontend-viewport-1099-chromium.png) |

## Remaining limitation

The native Windows app surface exposed no targetable Narrator window in this session, and the available computer-use browser surface cannot observe speech or Narrator Speech Recap. Therefore this run does not claim that the `role="status"` save/reset messages or `role="alert"` error message are spoken. The audible screen-reader sub-check remains `PARTIAL`/unverified and should be completed in a user-controlled Windows Narrator session by repeating save, reset, validation-error, and recovery, then checking Speech Recap with `Narrator+Alt+X`.

The official launcher cache failure is an environment residue boundary, not an application defect: the npm log showed repeated `EACCES` while extracting cached tarballs under `runtimes/cache/npm`. `npm ci` succeeded with a task-owned temporary cache, and all temporary data, logs, browser downloads, and helper processes were removed after validation. No process remains on ports `8890` or `8051`.
