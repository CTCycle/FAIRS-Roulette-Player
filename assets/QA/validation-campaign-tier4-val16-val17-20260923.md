# Validation campaign: VAL-16 and VAL-17

- Date: 2026-09-23
- Branch: `develop`
- Validated application/evidence commit: `2e9204a09a54b38a8169cd7b8cc52f55a559d09f`
- Hosted CI run: [35879722209](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/35879722209)

## Result

| Gate | Final status | Evidence |
| --- | --- | --- |
| `VAL-16` guidance and accessibility | `VALIDATED` for the tested Chromium desktop profile | Training and Inference keyboard, focus, persistence, accessible dialog names, and reduced-motion regressions passed; manual in-app browser spot checks passed. |
| `VAL-17` desktop visual coverage | `VALIDATED` for 1440×900 and 1100×800, with the 1099px minimum-width boundary checked | Training, Inference, and Settings page captures plus setup, summary, active Training, active Inference, and 1099px captures are retained below. |
| `persistence.postgresql` / `ISSUE-002` | `VALIDATED` / closed | Hosted `persistence-conformance` job 107244752370 passed on the same commit with PostgreSQL 17.11. |

The campaign and `frontend.workflows` remain `PARTIAL`: later hardware/maintenance/resilience gates and the separate frontend test-script gap remain open. Local PostgreSQL checks still skip without `TEST_POSTGRES_URL`, and no local listener on port 5432 was present; the hosted service-backed job supplies the conformance evidence for this revision.

## Environment and isolation

- Windows 11 Pro, build 26200; managed Python 3.14.7; Node 22.13.0; SQLite 3.50.4.
- CPU execution, one application worker; standard runner services on ports 8890 (backend) and 8051 (frontend).
- The official FAIRS run configuration pointed `FAIRS_DATA_DIR` at a temporary SQLite copy. The copy contained dataset `5` and checkpoint `val00_lineage_20260921`; all mutable Training and Inference activity used this copy. The canonical SQLite database was not used for mutations.
- The supported screen sizes were rendered in Chromium at 1440×900 and 1100×800. The boundary view was 1099×800.

## VAL-16 — Training and Inference guidance

`app/tests/e2e/test_guidance.py` now verifies both pages. The tests open the Help dialog and walkthrough using accessible names, assert dialog semantics (`role=dialog`, `aria-modal`, labelled/described relationships), check initial focus, cycle Tab and Shift+Tab within the walkthrough, dismiss with Escape, and verify focus returns to Help. They verify that dismissal persists in `localStorage` across reload for both the Training introduction and Inference loop. Both pages also render the guidance media with `prefers-reduced-motion: reduce` and assert its computed animation is `none`.

The keyboard regression exposed focus dropping to the document after moving Next and then Back: the previously focused Back control had become disabled. `GuidedTour` now detects focus that is outside the active dialog or on a disabled control after a step change and restores it to the dialog’s close button. The browser regression verifies containment and subsequent Escape/focus restoration.

Manual in-app browser checks confirmed the Training and Inference Help/walkthrough flows and visible keyboard focus behavior. Screen-reader software was not used, so assistive-technology announcement behavior is not claimed.

## VAL-17 — desktop views and active states

The added `app/tests/e2e/test_val16_val17_visuals.py` renders Training, Inference, and Settings at both supported desktop sizes, checks the relevant headings and controls, and asserts there is no horizontal document overflow. At 1099px it asserts the minimum-width notice is visible, the main layout remains 1100px, and Inference retains its two-column layout. These routes recorded zero page errors, console errors, failed requests, or HTTP responses at or above 400.

The setup capture exposed the Training wizard overlay being positioned against a transformed application wrapper, leaving the dialog below the viewport. `DatasetPreview` now portals the wizard overlay to `document.body`. A browser assertion verifies that portal location and that the dialog’s full bounds fit within the 900px viewport. The active captures came from a real dataset-backed CPU Training run and a checkpoint-backed Inference session; each was stopped through the UI.

The short Training run used perceptive-field size 8. The default size 64 is correctly rejected for dataset 5 because its validation partition is smaller than the field; this is a configuration constraint, not a product defect.

### Retained screenshots

| Scenario | Screenshot |
| --- | --- |
| Training, 1440×900 | [val17-training-1440x900.png](val17-training-1440x900.png) |
| Training, 1100×800 | [val17-training-1100x800.png](val17-training-1100x800.png) |
| Inference, 1440×900 | [val17-inference-1440x900.png](val17-inference-1440x900.png) |
| Inference, 1100×800 | [val17-inference-1100x800.png](val17-inference-1100x800.png) |
| Settings, 1440×900 | [val17-settings-1440x900.png](val17-settings-1440x900.png) |
| Settings, 1100×800 | [val17-settings-1100x800.png](val17-settings-1100x800.png) |
| Inference minimum-width boundary, 1099×800 | [val17-inference-minimum-boundary-1099x800.png](val17-inference-minimum-boundary-1099x800.png) |
| Training setup wizard, 1440×900 | [val17-training-setup-1440x900.png](val17-training-setup-1440x900.png) |
| Training wizard summary, 1440×900 | [val17-training-summary-1440x900.png](val17-training-summary-1440x900.png) |
| Active Training monitor, 1440×900 | [val17-training-active-1440x900.png](val17-training-active-1440x900.png) |
| Active Inference session, 1440×900 | [val17-inference-active-1440x900.png](val17-inference-active-1440x900.png) |

This retained route/boundary evidence also fills the screenshot-retention gap recorded in the original VAL-02 row; it supplements rather than rewrites the historical VAL-02 run.

## Verification results

- `npm run lint` — passed.
- `npm run build` — passed.
- Full standard Windows runner — `259 passed, 6 skipped in 214.66s`; live-server, Python, and frontend-bootstrap phases passed. The three new VAL-17 tests passed. Five local PostgreSQL cases skipped without `TEST_POSTGRES_URL`; one optional learned-strategy test skipped because the clean fixture did not contain that checkpoint.
- After adding the final Training reduced-motion assertion, the standard runner targeted at `app/tests/e2e/test_guidance.py` — `2 passed in 3.59s`.
- The standard runner reports its frontend unit and frontend E2E npm-script phases as `SKIPPED`; `ISSUE-003` remains open by scope choice.
- The runner printed the existing Italian `cmd.exe` input-redirection warning twice during service startup, but both readiness checks passed and all executed test phases completed successfully.
- Hosted CI for commit `2e9204a09a54b38a8169cd7b8cc52f55a559d09f`: `backend-validation`, `frontend-validation`, and `persistence-conformance` all passed. The PostgreSQL 17.11 persistence contract job completed at 2026-09-23 15:12:35 UTC. Its job details are available at [job 107244752370](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/35879722209/job/107244752370).

A standalone focused `pytest` invocation made after the standard runner had shut down its managed services received `ERR_CONNECTION_REFUSED`; it did not reach the application. The guidance tests were rerun through `run_tests.bat` with its managed services and passed, and the full runner had already passed the complete visual slice.

## Remaining gates and limitations

- `frontend.workflows` and `validation.campaign` remain `PARTIAL`. The UI check covers Chromium desktop behavior; screen-reader announcements, additional browsers, and physical-device behavior were not tested.
- `ISSUE-003` remains open: the frontend package still has no standalone unit/E2E npm scripts. The standard runner continues to label those phases `SKIPPED`.
- `VAL-18` remains a separate CUDA/device/JIT/mixed-precision task; hardware availability alone is not validation. `VAL-19` maintenance utilities remain open. `VAL-20` remains conditional. `VAL-21` and `VAL-22` remain later resilience work; conditional `VAL-09` is unchanged.
- `persistence.postgresql` is now validated by the hosted PostgreSQL 17.11 job; no local PostgreSQL URL or listener was configured, so local service-backed tests remain skipped.
- `runtime.source-release` remains `WORKING` pending the next release gate, and `distribution.packaged-artifacts` remains `NOT_IMPLEMENTED` under the source-only distribution scope.
