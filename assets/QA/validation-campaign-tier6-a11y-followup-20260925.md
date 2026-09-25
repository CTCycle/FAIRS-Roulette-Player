# Tier 6 Accessibility Follow-up

- Date: 2026-09-25
- Branch: `develop`
- Tested revision: `192c70b5cf35db8d9ba61fc1d7e16aa72fed52af`
- Scope: Revalidate the remaining `A11Y-01` accessibility slice and repeat the current frontend test gates and launcher dependency boundary.

## Gate disposition

| Gate | Final status | Current result |
| --- | --- | --- |
| `A11Y-01` | `PARTIAL` | Live isolated Settings save, reset, invalid-input, valid-recovery, and reload-persistence states were re-exercised. Visible feedback was exposed in the browser accessibility tree and the source retains the expected live-region and field-error semantics. Native Narrator speech and Speech Recap remained unobservable. |
| `frontend.workflows` | `PARTIAL` | No current product defect was reproduced. The remaining limitation is audible speech verification; phone/mobile layouts remain outside the supported desktop specification. |
| `validation.campaign` | `PARTIAL` | All current client checks and live desktop states passed; the audible announcement sub-check remains incomplete. |
| `STARTUP-01` | `VALIDATED` with host setup limitation | The official cold launcher again reached frontend `npm ci` and failed on protected canonical-cache entries. A task-owned cache installed the same dependency lock successfully, after which the live backend/frontend workflow passed. |

## Live isolated workflow

The frontend was rebuilt from the current checkout and served on `127.0.0.1:8051`. The backend ran as one Uvicorn worker on `127.0.0.1:8890` against a temporary SQLite/data root copied from the current application state. The temporary root was removed after the run.

In Chrome at the supported desktop width, the following transitions were completed:

1. Minimum `0` → `1` → Save: the accessibility tree exposed `Settings saved.`, and the Save control became disabled after persistence.
2. Reset to defaults: the tree exposed `Settings reset to defaults.` and Minimum returned to `0`.
3. Invalid Minimum `37` → Save: the tree exposed `Il valore deve essere inferiore o uguale a 36.` and the source inspection confirmed `role="alert"`, `aria-invalid`, and `aria-describedby`.
4. Recovery to Minimum `1` → Save → reload: the error disappeared, `Settings saved.` returned, and the reloaded page retained value `1`.
5. Reset after the check restored the isolated data root to the documented defaults.

The backend log recorded healthy startup and the expected `GET /api/health`, `GET /api/settings`, `PATCH /api/settings`, and `POST /api/settings/reset` requests. No application error or failed request was observed in the live workflow.

## Current-tree automated checks

| Check | Result | Evidence |
| --- | --- | --- |
| Vitest unit suite | `11 passed` across 3 files | [`frontend-a11y-followup-unit-20260925.log`](frontend-a11y-followup-unit-20260925.log) |
| Mocked browser suite | `4 passed` using the installed Chrome channel | [`frontend-a11y-followup-e2e-20260925.log`](frontend-a11y-followup-e2e-20260925.log), [`frontend-e2e-junit-chromium.xml`](frontend-e2e-junit-chromium.xml) |
| Frontend lint | Passed | [`frontend-a11y-followup-lint-20260925.log`](frontend-a11y-followup-lint-20260925.log) |
| Production build | Passed; TypeScript plus Vite transformed `1771` modules | [`frontend-a11y-followup-build-20260925.log`](frontend-a11y-followup-build-20260925.log) |
| Desktop boundary | Current Chromium captures show the documented `1099px` warning and supported `1100px` workspace | [`frontend-viewport-1099-chromium.png`](frontend-viewport-1099-chromium.png), [`frontend-viewport-1100-chromium.png`](frontend-viewport-1100-chromium.png) |

## Remaining limitations

The preinstalled Narrator process could not start in this session (`0xc0000142`), and the computer-use app inventory exposed no targetable native Narrator window. The browser accessibility tree and source semantics therefore do not prove audible speech. `A11Y-01` remains `PARTIAL`; a user-controlled Windows Narrator session must repeat the four feedback states and inspect Speech Recap with `Narrator+Alt+X`.

The official launcher dependency attempt failed in the protected canonical cache: the npm debug log records repeated `EACCES` while fetching cached tarballs and ends with `Exit handler never called`. `npm ci` then succeeded with a task-owned cache and did not require any permissions change or canonical-cache deletion. The default Playwright headless executable was also absent from the default user cache; the same four E2E cases passed through the installed Chrome channel. These are environment/setup limits, not application defects.
