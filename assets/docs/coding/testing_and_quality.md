## Testing And Quality

Last updated: 2026-10-23

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

At `bcf8f00` on Windows with Python 3.14.7, the seeded repository-standard runner exited 0: 259 Python cases collected, 254 passed and 5 skipped in 256.79 seconds. The five skips require a local PostgreSQL service; the optional strategy-suggestion case passed with the seeded checkpoint. The production build passed in 3.81 seconds, Vitest passed 11/11 in 0.372 seconds, Playwright passed 7/7 in 11.0 seconds, and Ruff passed. Dataset 5 used the expected `val00_training_lineage` name and 120 rows, with the required checkpoints trained through the local API. The temporary data/cache root was removed, the temporary `FAIRS_DATA_DIR` override was cleared, and test ports 8890/8051 were clear.
- Set `STANDARD_TEST_CACHE_ROOT` before invoking `app/tests/run_tests.bat` to place all runner caches, including pytest basetemp and Playwright browser storage, under an isolated root. Without it, the runner uses `runtimes/cache`.
- `.github/workflows/ci.yml`
  - Linux CI runs the backend Ruff/unit/Alembic/OpenAPI/PostgreSQL checks and a separate frontend lint/build job. Python dependencies resolve from `app/server/pyproject.toml` when `uv.lock` is absent, while the repository-root `ruff.toml` owns Ruff’s canonical cache path; generated QA assets are excluded from lint traversal.

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
