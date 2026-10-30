## Testing And Quality

Last updated: 2026-10-30

## Quality Baseline

- Prefer small, well-scoped changes over broad rewrites.
- Keep docs synchronized with behavior changes in the same change set.
- Treat typing, linting, and relevant tests as part of the definition of done.

## Python Validation

- Lint and format with Ruff or the repository-equivalent configured tooling.
- Follow a Pylance-compatible type discipline.
- Prefer targeted `pytest` execution when changing narrow backend behavior.
- Expand to broader unit or e2e coverage when changes cross module boundaries.

## Frontend Validation

- Use the existing npm scripts for linting and build validation.
- Keep parser logic strict at the current snake_case contract boundary; reject malformed, aliased, or legacy payloads instead of silently defaulting them.
- Validate UI behavior visually when user-facing layout or interaction changes are involved.
- The frontend package provides `test:unit` for client-owned payload, parser, and session-storage behavior, plus `test:e2e` for mocked Training, Inference, Settings, and supported desktop-width paths. Keep real backend lifecycle behavior in the Python Playwright suite.
- CI runs the Windows PowerShell launcher maintenance harness on `windows-latest`, including live process-tree cleanup for both running and already-exited parents. This complements, but does not replace, the locally observed interactive `-Launch` and Ctrl+C smoke. CI enforces the frontend gate in `.github/workflows/ci.yml` with Node 22: `npm ci`, Chromium installation, `npm run test:unit`, `npm run lint`, `npm run build`, and `npm run test:e2e` from `app/client`. A checked-in `package-lock.json` is required.

## Test Layout

Primary automated test surfaces live under `app/tests`:

- `app/tests/unit`
  - 10 cohesive suites for startup/configuration, persistence/settings, data/checkpoint/security, training, inference/roulette, API contracts, architecture/cache, and Windows maintenance
- `app/tests/e2e`
  - 9 suites for browser workflows, API behavior, persistence, and validation campaigns
- `app/client/tests/unit/clientBehavior.test.ts`
  - client payload, parser, and inference-session persistence behavior
- `app/client/tests/e2e/frontend.spec.ts`
  - mocked client workflows and the supported desktop-width boundary
- `app/tests/run_tests.bat`
  - repository-standard Windows test entry point; synchronizes the test extra and ensures Playwright Chromium is installed below `runtimes/cache/playwright-browsers` before collection
- `app/tests/unit/test_windows_launcher_maintenance.py` invokes the Windows PowerShell harness and skips on non-Windows even when `pwsh` is installed
- `pytest.ini`
  - keeps pytest's cache and basetemp under `runtimes/cache/pytest` and `runtimes/cache/pytest-tmp`, limits collection to `app/tests/unit` and `app/tests/e2e`, and excludes generated/cache directories; Ruff and other test tooling use sibling paths below `runtimes/cache`
- `app/tests/e2e/test_validation_campaigns.py`
  - combines VAL-16/17 visuals and VAL-21/22 resilience with independent `val16_17`, `val21`, and `val22` marks; VAL-18 remains in the separate hardware-only suite

Select an individual campaign with `pytest app/tests/e2e/test_validation_campaigns.py -m val21`; run the consolidated campaigns with `-m "val16_17 or val21 or val22"`. Pytest's default selection still includes all three.

The repository now has 21 test modules across the backend and frontend. Tests were grouped by behavior; the two overlapping desktop-boundary and checkpoint-deletion checks were combined while their unique assertions remain covered.

### Consolidation Record (2026-10-22)

The suite moved from 48 test modules and 279 cases to 21 modules and 277 cases. The two removed cases duplicated behavior now asserted by broader desktop-width and checkpoint-lifecycle tests. The two support scripts remain active, as do both frontend test commands; no test dependency or CI command was removed because each remains in use.

The seeded Windows standard runner passed 253 Python cases and skipped 6 of 259 collected in 235.80 seconds. Five skips require PostgreSQL service coverage, and one optional strategy case had no suggestion to assert. Vitest passed 11/11 in 0.288 seconds, Playwright passed 7/7 in 10.1 seconds, the production build passed in 2.59 seconds, and Ruff passed. The disposable data/checkpoint root was removed and settings/.env was restored byte-for-byte.

### Current standard-suite revalidation (2026-10-23)

At `bcf8f00` on Windows with Python 3.14.7, the seeded repository-standard runner exited 0: 259 Python cases collected, 254 passed and 5 skipped in 256.79 seconds. The five skips require a local PostgreSQL service; the optional strategy-suggestion case passed with the seeded checkpoint. The production build passed in 3.81 seconds, Vitest passed 11/11 in 0.372 seconds, Playwright passed 7/7 in 11.0 seconds, and Ruff passed. Dataset 5 used the expected `val00_training_lineage` name and 120 rows, with checkpoints `val00_lineage_20260921` and `val15_strategy_20260923` trained through the local API. The first seed attempt used a mismatched name and row count, causing four stored-dataset wizard cases to fail; after correcting the seed, all four passed and no product change was needed. The temporary data/cache root was removed, the temporary `FAIRS_DATA_DIR` override was cleared, and test ports 8890/8051 were clear. A preceding blocked-service diagnostic was interrupted before its byte-restoration handler ran. Although the temporary data-root override was cleared, the `.env` hash differed from the value observed before that diagnostic, so exact byte-for-byte restoration is unverified for this run.

### Consolidated QA evidence (2026-10-25)

The ignored `assets/QA/` bundle was reviewed and its durable findings are captured below and in the project status ledger. It contained 20 screenshots, the 2026-10-23 runner Markdown report and raw log, a frontend JUnit report, and Playwright's last-run summary. It contained no standalone dataset or checkpoint fixture files: the seed lived in a disposable data root, and the required checkpoints were trained through the application API. The raw outputs were removed after this summary; source tests remain the reproducible test specification.

| Captured material | Durable observation |
| --- | --- |
| `fairs_startup_loading.png`, `fairs_startup_loading_1100x800.png`, `fairs_startup_loading_1440x900.png` | The 1280×720, 1100×800, and 1440×900 captures show the same startup state: “Preparing the table…”, “Starting the FAIRS backend.”, and “Waiting for a healthy response.” |
| `frontend-viewport-1099-chromium.png`, `frontend-viewport-1100-chromium.png` | At the below-minimum width, the Training page displays the “Desktop window required” notice stating that FAIRS needs at least 1100px. At 1100px the full Training workspace is visible. These are mocked frontend captures using a 100-row `Frontend fixture` dataset and `frontend-checkpoint`. |
| `val12-inference-history-replay.png` | Inference history shows a confirmed first prediction of number 7, observed 7, +350 outcome, and capital 1350; a second prediction is pending. The session summary reports one completed step and the number-7 suggestion. |
| `val13-inference-replacement-rollback.png` | The injected VAL-13 replay error is visible while the original session remains usable: two settled losing rows, a third pending row, capital 980, and two completed steps. This is the expected failure-injection state used to observe rollback. |
| `val14-inference-restart-recovered.png` | After restart recovery, the browser is in an idle session state with capital 1000, zero steps, empty history, and no pending prediction. Persistence of the ended session's audit history is established by the gate evidence in the status ledger, not by this image alone. |
| `val15-strategy-suggestion.png` | Checkpoint `val15_strategy_20260923` displays a D'Alembert suggestion for number 16 with a €10 bet, capital 1000, and zero settled steps. The later UI recheck produced Martingale; this earlier screenshot is not the later result. |
| `val17-training-1100x800.png`, `val17-training-1440x900.png`, `val17-training-setup-1440x900.png`, `val17-training-active-1440x900.png`, `val17-training-summary-1440x900.png` | The 1100×800 and 1440×900 Training views show four 160-row `codex_validation_seed_*` datasets, the 120-row `val00_training_lineage` dataset, and checkpoints `val00_lineage_20260921` and `val15_strategy_20260923`. The wizard setup snapshot shows step 1 of 6 with perceptive field 64, QNet neurons 64, embedding dimensions 200, update frequency 10, explore rate 0.75, decay 0.995, minimum explore rate 0.1, and discount rate 0.5. The step 6 summary uses checkpoint `val16_visual_8ed4558d47` on `val00_training_lineage` with perceptive field 8, 64 neurons, 200 embedding dimensions, and update frequency 10. The active-monitor snapshot shows episode 1/10, step 169/2000, 1% progress, replay warm-up 170/1000, capital 310, and total reward -690; these are captured run values, not defaults. |
| `val17-inference-1100x800.png`, `val17-inference-1440x900.png`, `val17-inference-active-1440x900.png`, `val17-inference-minimum-boundary-1099x800.png` | The supported-width captures show the Inference setup and empty history at 1100×800 and 1440×900; the active snapshot shows one pending number-7 prediction on `val00_lineage_20260921`. At 1099px, the minimum-width notice is shown over the Inference layout. |
| `val17-settings-1100x800.png`, `val17-settings-1440x900.png` | Both supported-width Settings captures show roulette numbers 0–36 with zero included. |

The Chromium JUnit output reported 7 tests, 0 failures, 0 errors, and 0 skips. Its scenarios were: “Training wizard advances and returns to a selected step”; “Inference setup loads checkpoint and dataset options”; “Settings changes save automatically and survive a reload”; “Settings debounces continuous edits and preserves later changes after a failed write”; “Settings retries a newer immediate edit queued during a failed write”; “Database fields stay as a draft until the explicit switch action”; and “1100px is supported and 1099px shows the minimum-width notice.” The five Python skips were `test_postgresql_clean_and_current_are_idempotent`, `test_postgresql_unversioned_database_is_rejected_without_mutation`, `test_postgresql_synthetic_rollback_and_behind_revision`, `test_postgresql_concurrent_initializers_serialize`, and `test_postgresql_contract`; they require a local PostgreSQL service. Hosted PostgreSQL conformance is recorded separately in the status ledger. Playwright's `.last-run.json` also reported `passed` with no failed tests. These generated summaries duplicate the source test coverage and the results above; they are not separate evidence dependencies.
- Set `STANDARD_TEST_CACHE_ROOT` before invoking `app/tests/run_tests.bat` to place all runner caches, including pytest basetemp and Playwright browser storage, under an isolated root. Without it, the runner uses `runtimes/cache`.
- `.github/workflows/ci.yml`
  - The workflow has four gates: Linux backend validation (locked `uv` test dependencies, Ruff, unit tests, Alembic heads, and generated frontend-contract check); PostgreSQL 17 persistence conformance; frontend validation (Node 22.13.0, `npm ci`, Chromium, unit tests, lint, production build, and browser E2E); and Windows launcher maintenance (PowerShell). Ruff uses the repository-root `ruff.toml` and excludes generated QA assets.

## Migration Validation

- Keep the immutable baseline aligned with all four current SQLAlchemy tables, indexes, named checks/unique constraints, and foreign-key cascade semantics.
- Use test-only synthetic revisions for behind-version and rollback cases; do not add failure-only revisions to production history.
- Validate clean/current databases, rejection of non-empty unversioned and partial schemas, unknown/ahead revision rejection, rollback, and concurrent SQLite initialization. Run PostgreSQL persistence migration coverage when the service is available.

## Change Expectations

- Run the smallest relevant test slice first.
- Use broader checks when shared infrastructure or startup flow changes.
- Treat `assets/QA/` as an ignored transient output path for runner logs, JUnit results, traces, and screenshots; it is not a durable evidence store.
- After a validation slice, synthesize the result, limitation, defect history, exact revision, and follow-up into the project status ledger. Keep only source tests, implementation docs, hosted CI links, and approved product figures as durable traceability.
- Do not leave temporary logs, screenshots, or validation scraps scattered through the repository.

## Comprehensive Validation Campaign

The canonical campaign tracker is [`../project_status_ledger.md`](../project_status_ledger.md). The campaign targets the core Windows + SQLite + CPU profile first, then treats PostgreSQL, CUDA, mixed precision, JIT, maintenance, and resilience as explicit validation boundaries. Its dependency order is:

`startup → persistence/settings → datasets → training → checkpoint → inference`

Use the documented, code-backed roadmap slice IDs in the ledger. The normal execution order is `VAL-00 → VAL-01 → VAL-02 → VAL-04 → VAL-06 → VAL-07 → VAL-08 → VAL-10 → VAL-11 → VAL-12 → VAL-13 → VAL-14 → VAL-15 → VAL-16 → VAL-17 → VAL-19 → VAL-21 → VAL-22 → VAL-23`; run `VAL-03` and `VAL-05` when their dependencies or evidence change, and run `VAL-18` after relevant hardware or runtime changes. `VAL-23` covers the Settings database connection-test, switch, rollback, and per-database isolation path. Do not create or infer a validation gate without a corresponding code-backed capability, trigger, and acceptance contract.

For every slice use:

`Inspect → Execute → Observe → Diagnose → Fix → Retest → Regress → Record`

Record only scenarios actually executed, the exact source revision, environment, stable issue IDs, classification, root cause, remediation, adjacent regression, evidence paths, and remaining gaps. Browser evidence includes the rendered state, console errors, failed network requests, backend errors, and screenshots for failures. DOM roles, accessibility-tree text, and visible feedback do not prove spoken screen-reader output; a spoken accessibility claim requires a user-controlled Windows Narrator/Speech Recap observation. Persistence/model evidence also includes database state and dataset, checkpoint, session, or job identifiers. Store transient runner output under `assets/QA/` only as needed during execution, then move the durable conclusion and limitation into the tracked ledger and remove redundant artifacts.

The first active tier is Tier 0:

- `VAL-00` creates or identifies one disposable training dataset and produces a real short CPU checkpoint through the supported application path. This lineage is the prerequisite for live inference validation; mocked checkpoints do not satisfy the campaign.
- `VAL-01` smoke-tests the official Windows launcher, frontend-before-backend loading, `/api/health` transition, route entry, explicit owned-process shutdown, and port cleanup. It does not certify Training or Inference behavior after route mount.

Use repository-local cache/temp paths and preserve unrelated data or processes. Do not infer a pass from source presence, a test definition, an HTTP 200 alone, or a hosted result from a different revision. The current consolidated gate result is in [`../project_status_ledger.md`](../project_status_ledger.md). The 2026-10-21 Windows standard runner passed `255` Python tests with `6` skips, plus frontend build, `11/11` Vitest, and `7/7` Playwright. VAL-17, VAL-21, and VAL-18 passed. VAL-23 passed through the live Settings API against a disposable PostgreSQL 18 cluster, covering connection test/rejection, switching, rollback, and independent preferences; this check did not drive the PostgreSQL switch through a browser. Hosted backend, PostgreSQL persistence, and frontend CI all passed on release commit `10dbef0` in both the develop run [39658086984](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/39658086984) and main run [39658338088](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/39658338088). Candidate-local checks passed Ruff, all `157` backend unit tests, `8` Settings API/SQLite restart E2E cases, Alembic head, generated-contract checks, and the offline lock check. `STARTUP-01`, the launcher interactive-stop smoke, the browser-driven PostgreSQL switch, and the frontend workflow's spoken-accessibility follow-up retain their documented boundaries.

## Related Files

- Read `python.md` for backend implementation rules.
- Read `typescript.md` for frontend implementation rules.
- Read `../operations/troubleshooting.md` for common runtime and test recovery checks.
