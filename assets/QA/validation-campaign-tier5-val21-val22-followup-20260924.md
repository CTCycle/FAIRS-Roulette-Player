# Tier 5 VAL-21/VAL-22 current-tree revalidation

- Date: 2026-09-24
- Status: `VALIDATED` for both slices
- Source/test revision: `c6a4a8d5f9c6e72c2828c852f4d2e14b2789964f`
- Detailed run output: [focused pytest log](validation-campaign-tier5-val21-val22-final-20260924-163609.log)

## Selection

The current working changes expanded the already-completed Tier 5 resilience tests. VAL-21 and VAL-22 form one manageable revalidation scope: input rejection and recovery checks, plus repeated lifecycle, persistence, capacity, cleanup, and state-leak checks. The `VAL-22` reset assertion was corrected to include the existing roulette defaults; no application source behavior changed.

The conditional VAL-09 and VAL-20 gates and the frontend coverage gaps were reviewed separately below. They do not share an executable boundary with these backend resilience tests.

## Environment and isolation

- Windows 11 Pro build `26200`; project environment Python `3.14.7`; SQLite `3.50.4`; one Uvicorn worker.
- The run used Playwright `APIRequestContext` against the live backend on an isolated loopback port. It did not exercise rendered UI.
- The canonical database was opened read-only and backed up into a fresh `%TEMP%` data root; runtime settings and the fixed checkpoint tree were copied there. Baseline checks passed: SQLite integrity `ok`, dataset `5` was `val00_training_lineage`, checkpoint `val00_lineage_20260921` existed, and there were zero active persisted inference sessions.
- The effective runtime root was verified before starting the server. `settings/.env` was restored byte-for-byte. The canonical database, runtime-settings file, and checkpoint tree matched their pre-run SHA-256 snapshots.
- The final isolated database passed `PRAGMA integrity_check`, had zero active inference sessions and zero `val21_*`/`val22_*` datasets. No test-owned listener remained after cleanup.

## VAL-21 result

The five VAL-21 tests passed. Malformed Settings, Training, and Inference requests returned deterministic `4xx` responses and health remained `200`. Rejected Settings and Training changes preserved persisted snapshots. Invalid Inference starts and operations preserved the complete persisted session/step state; valid bet, step, and replacement-session recovery succeeded.

Upload rejection returned `[422, 400, 400, 400, 413, 400]` for invalid kind, separator, content, workbook, over-limit file, and filename cases. The valid two-row recovery upload was deleted, and the before/after dataset state matched.

One first attempt ended with `ECONNRESET` while sending the over-limit multipart body. The isolated retry and final focused run both returned the expected `413`; the neighboring upload API regression also passed. This was not reproduced and no product defect was established.

## VAL-22 result

- Three live inference cycles created nine unique sessions. Each covered bet updates, two observed steps, corrected-history replay through replacement, row-removal replay through replacement, shutdown, and row clearing. Every session ended, every tested step row was cleared, the active-session set returned to empty, and the checkpoint list stayed at baseline. Maximum cycle time was `1.794s`.
- Ten Settings write/read/reset cycles persisted the full documented default response, including roulette settings; they left no temporary files. Maximum cycle time was `0.099s`, and the test restored the original settings document.
- Three Training cancellation/recovery cycles returned to idle and removed temporary checkpoints and staging. Maximum cycle time was `19.076s`, under the existing 45-second cancellation and 90-second recovery timeouts.
- Four application lifespan cycles disposed the database and shut down each service once per cycle. Capacity testing accepted 18 starts while holding the configured 16-session bound, ended the two evicted sessions, and released their model/context references. The telemetry test retained 2,000 points after 2,001 updates; four terminal-manager cleanup cycles released worker/thread references.

## Validation commands and result

The focused run covered all five VAL-21 cases, all three VAL-22 cases, the adjacent oversized-upload regression, and seven related lifecycle, replay/rollback, capacity, telemetry, and cleanup unit cases: **16 passed, 33 deselected in 73.45 seconds**. Ruff reported `All checks passed!`; `git diff --check` passed.

The first standard-runner selection reported 13 passed and two failures: the new reset assertion omitted the roulette defaults, and one over-limit upload connection reset. The assertion was corrected, both upload tests passed on isolated retry, and the final focused run passed all 16 cases. No application code change was needed.

The prior complete Windows runner (`274 passed, 6 skipped`) and hosted CI run `35987774300` remain evidence at predecessor revision `5f3ac3089810b798d07f1a055a6f8cb1d1754758`. This follow-up was a targeted local recheck; it did not repeat the full runner or hosted CI at `c6a4a8d`.

## Remaining incomplete gates reviewed

- **VAL-09:** remains conditional. No trigger changed, and the checked-in documentation still does not define its trigger or acceptance criteria. Do not promote until that contract exists and the trigger occurs.
- **VAL-20:** remains conditional. The adjacent Windows `eager`/`inductor` behavior has prior evidence, but the full trigger and acceptance contract are still absent from checked-in documentation. This recheck does not promote the gate.
- **`frontend.workflows`:** remains `PARTIAL` for screen-reader announcement behavior, additional browsers, and physical-device rendering. This API resilience slice did not test rendered UI.
- **`ISSUE-003` / `qa.frontend-test-scripts`:** remains open / `NOT_IMPLEMENTED`; the separate decision on standalone frontend unit/E2E scripts and representative UI paths remains outstanding.
- **`runtime.source-release`:** remains `WORKING` pending the next release gate. Packaged artifacts remain `NOT_IMPLEMENTED` and outside current product scope.
- No gate is currently `BLOCKED`. The overall validation campaign remains `PARTIAL` because the conditional gates and frontend coverage work remain open.
