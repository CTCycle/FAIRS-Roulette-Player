## Testing And Quality

Last updated: 2026-09-25

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
- CI enforces the frontend gate in `.github/workflows/ci.yml` with Node 22: `npm ci`, Chromium installation, `npm run test:unit`, `npm run lint`, `npm run build`, and `npm run test:e2e` from `app/client`. A checked-in `package-lock.json` is required.

## Test Layout

Primary automated test surfaces live under `app/tests`:

- `app/tests/unit`
  - unit and service-level validation
- `app/tests/e2e`
  - API and workflow coverage
- `app/tests/run_tests.bat`
  - repository-standard Windows test entry point; synchronizes the test extra and ensures Playwright Chromium is installed below `runtimes/cache/playwright-browsers` before collection
- `app/tests/unit/test_windows_launcher_contract.py` contains static launcher checks that can run on Linux; `test_windows_launcher_maintenance.py` invokes the Windows PowerShell harness and skips on non-Windows even when `pwsh` is installed
- `pytest.ini`
  - keeps pytest's cache and basetemp under `runtimes/cache/pytest` and `runtimes/cache/pytest-tmp`, limits collection to `app/tests/unit` and `app/tests/e2e`, and excludes generated/cache directories; Ruff and other test tooling use sibling paths below `runtimes/cache`
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
- Keep QA artifacts in `assets/QA/` when persistent evidence is needed.
- Do not leave temporary logs, screenshots, or validation scraps scattered through the repository.

## Comprehensive Validation Campaign

The canonical campaign tracker is [`../project_status_ledger.md`](../project_status_ledger.md). The campaign targets the core Windows + SQLite + CPU profile first, then treats PostgreSQL, CUDA, mixed precision, JIT, maintenance, and resilience as explicit conditional gates. Its dependency order is:

`startup → persistence/settings → datasets → training → checkpoint → inference`

Use the roadmap slice IDs `VAL-00` through `VAL-22` in the ledger. The normal execution order is `VAL-00 → VAL-01 → VAL-02 → VAL-04 → VAL-06 → VAL-07 → VAL-08 → VAL-10 → VAL-11 → VAL-12 → VAL-13 → VAL-14 → VAL-15 → VAL-16 → VAL-17 → VAL-19 → VAL-21 → VAL-22`; run `VAL-03` and `VAL-05` when their dependencies or evidence change, and run `VAL-18` after relevant hardware or runtime changes. Execute conditional VAL-09/20 only after their triggers and acceptance criteria are documented; do not infer missing gate contracts.

For every slice use:

`Inspect → Execute → Observe → Diagnose → Fix → Retest → Regress → Record`

Record only scenarios actually executed, the exact source revision, environment, stable issue IDs, classification, root cause, remediation, adjacent regression, evidence paths, and remaining gaps. Browser evidence includes the visible state, console errors, failed network requests, backend errors, and screenshots for failures. Persistence/model evidence also includes database state and dataset, checkpoint, session, or job identifiers. Store detailed QA artifacts under `assets/QA/`; keep the conclusion and limitation in the tracked ledger.

The first active tier is Tier 0:

- `VAL-00` creates or identifies one disposable training dataset and produces a real short CPU checkpoint through the supported application path. This lineage is the prerequisite for live inference validation; mocked checkpoints do not satisfy the campaign.
- `VAL-01` smoke-tests the official Windows launcher, frontend-before-backend loading, `/api/health` transition, route entry, explicit owned-process shutdown, and port cleanup. It does not certify Training or Inference behavior after route mount.

Use repository-local cache/temp paths and preserve unrelated data or processes. Do not infer a pass from source presence, a test definition, an HTTP 200 alone, or a hosted result from a different revision.

## Related Files

- Read `python.md` for backend implementation rules.
- Read `typescript.md` for frontend implementation rules.
- Read `../operations/troubleshooting.md` for common runtime and test recovery checks.
