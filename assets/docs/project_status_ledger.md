## Project Status Ledger

Last updated: 2026-09-21

## Purpose and authority

This document is the canonical catalog of the current operational state of FAIRS. It summarizes what is implemented, what has meaningful evidence, what is incomplete or blocked, and what must be revalidated. Detailed architecture, implementation, test, and remediation documents remain the evidence and design authorities for their own subjects.

The snapshot was bootstrapped from the `v3.4.2` checkout at baseline commit `25e2537`. The authorized Development reinstall migrated the managed runtime to Python `3.14.7`, resolved PyTorch `2.10.0+cu130`, recreated the backend environment, installed Playwright browsers, rebuilt the frontend, and preserved the SQLite database. The current validation result is `199 passed, 9 skipped, 1 warning`; the detailed migration evidence is recorded in [`assets/QA/python314-migration-validation-20260921.md`](../QA/python314-migration-validation-20260921.md). No application capability is promoted to `VALIDATED` from source presence or test definitions alone.

The nine pytest skips were explicit: five PostgreSQL cases without `TEST_POSTGRES_URL` and four checkpoint-backed inference cases without a usable fixture. The runner separately reported frontend unit and frontend E2E phases as `SKIPPED` because those npm scripts do not exist. The Python 3.14 launcher/browser/ML smoke is documented under `assets/QA/`; this ledger keeps the current result compact and links to the runner, test sources, and the smoke note.

## Maintenance rules

Future coding agents must:

1. Read this ledger before substantial implementation or validation work.
2. Use it to find known defects and previously validated behavior.
3. Update affected entries after implementation changes.
4. Add current validation evidence after meaningful tests or manual checks.
5. Never mark a component `VALIDATED` without a recorded result and supporting reference.
6. Downgrade a status when a regression is observed.
7. Close or move an issue to the historical section only after remediation and revalidation.
8. Avoid duplicate issue entries for the same underlying defect.
9. Link detailed reports, tests, and plans instead of copying their narratives here.
10. Keep this ledger synchronized with the actual repository state.

## Status taxonomy

| Status | Meaning |
| --- | --- |
| `VALIDATED` | Implemented and confirmed through meaningful current testing or manual validation. |
| `WORKING` | Believed to work from implementation and limited or indirect evidence, but not fully validated. |
| `PARTIAL` | Implemented, but incomplete, degraded, or valid for only part of the expected behavior. |
| `BROKEN` | Known not to work correctly. |
| `BLOCKED` | Cannot currently be validated or completed because an external dependency, service, credential, hardware constraint, or similar blocker is unavailable. |
| `UNVALIDATED` | Implementation exists, but current evidence is insufficient to claim that it works. |
| `NOT_IMPLEMENTED` | The expected capability is absent from this checkout. |
| `DEPRECATED` | Retained only for compatibility or scheduled for removal. |

`Validation Level` uses `None`, `unit`, `integration`, `E2E`, `manual`, or a combination such as `unit + E2E`. `None` means that no current meaningful result is available; the existence of tests does not change that value. Severity in the issue catalog is independent from component status.

## Current status summary

| Status | Components in this snapshot |
| --- | --- |
| `VALIDATED` | `docs.ontology`, `application.startup`, `backend.api-contracts`, `backend.training`, `persistence.sqlite`, `runtime.settings`, `qa.standard-runner` |
| `WORKING` | `runtime.source-release` |
| `PARTIAL` | `backend.inference`, `frontend.workflows` |
| `BROKEN` | None evidenced in the current checkout. |
| `BLOCKED` | `persistence.postgresql` |
| `UNVALIDATED` | None current; remaining uncertainty is recorded as `PARTIAL`, `BLOCKED`, or validation debt. |
| `NOT_IMPLEMENTED` | `qa.frontend-test-scripts`, `distribution.packaged-artifacts` |
| `DEPRECATED` | None current. |

## Current component ledger

| Component | Status | Scope | Evidence | Known Issues | Blocker | Last Validated | Validation Level | Related Docs | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `docs.ontology` | `VALIDATED` | Root index, lower-case topic branches, dated leaf documents, and ledger discoverability. | The complete `assets/docs/` tree and its naming/link conventions were inspected; the root index now links this ledger and the post-edit links resolve. | None evidenced. | — | 2026-09-20 | `manual` | [`project_index.md`](project_index.md) | Update the index and ledger together when document roles or state evidence change. |
| `runtime.source-release` | `WORKING` | Source-only distribution boundary and current application version. | `app/server/pyproject.toml` reports `3.4.2`; the inspected baseline is tagged `v3.4.2`; deployment documentation defines source distribution and annotated-tag release rules. | No installer, container, desktop package, or bundled executable is supported by this checkout. | — | 2026-09-20 | `manual` | [`deployment.md`](runtime/deployment.md), [`modes.md`](runtime/modes.md) | On the next release, recheck synchronized `main`, hosted CI, tag ancestry, and version metadata. |
| `application.startup` | `VALIDATED` | Windows launcher preparation, database startup, backend health, frontend readiness, single-worker lifecycle, and stop behavior. | Python 3.14.7 Development reinstall, standard runner, direct launcher option 1, backend-stop simulation with the frontend still serving, waiting-screen animation measurement, supported viewport checks, production build, and process/port cleanup all passed. | Browser opening remains best-effort by design; the runner's standalone frontend unit/E2E phases remain skipped because those npm scripts do not exist. | — | 2026-09-21 | `manual + E2E` | [`startup.md`](runtime/startup.md), [`deployment.md`](runtime/deployment.md), [`test_app_entrypoint.py`](../../app/tests/unit/test_app_entrypoint.py), [`app_flow.py`](../../app/tests/e2e/test_app_flow.py), [`../QA/python314-migration-validation-20260921.md`](../QA/python314-migration-validation-20260921.md) | Re-run the launcher smoke and startup browser slice after future launcher or bootstrap changes. |
| `backend.api-contracts` | `VALIDATED` | FastAPI routers, Pydantic contracts, health/system, upload, training, inference, settings, and generated frontend transport types. | Standard suite: `199 passed`; generated frontend contract check passed; route-specific API and browser tests passed; Ruff passed. | Full live inference-session routes remain outside this result because four tests skipped without a checkpoint/data fixture; PostgreSQL is tracked separately. | — | 2026-09-21 | `unit + E2E` | [`backend_api.md`](architecture/backend_api.md), [`execution_and_data_flow.md`](architecture/execution_and_data_flow.md), [`test_generated_contracts.py`](../../app/tests/unit/test_generated_contracts.py) | Re-run the contract and affected route slices after API or schema changes. |
| `backend.training` | `VALIDATED` | Dataset preparation, training validation/start/status/stop/resume, worker lifecycle, metrics, and checkpoint production. | Python 3.14 standard suite covered training start, status, stop, cancellation, resume, unit/service behavior, and data contracts; all executed cases passed. | No failure observed; compute-heavy runtime and checkpoints should be rechecked after learning or worker changes. | — | 2026-09-21 | `unit + E2E` | [`execution_and_data_flow.md`](architecture/execution_and_data_flow.md), [`workflows.md`](operations/workflows.md), [`test_training_api.py`](../../app/tests/e2e/test_training_api.py) | Repeat the training E2E workflow after changes to workers, checkpoints, data preparation, or training contracts. |
| `backend.inference` | `PARTIAL` | Process-local inference sessions, prediction steps, bet updates, row/context clearing, shutdown, and persisted history. | Inference service unit lifecycle/prediction tests and invalid-session API tests passed; page navigation and inference-page rendering passed. | Four live inference-session E2E tests skipped because the test environment had no usable checkpoint/data fixture; live model state intentionally expires on backend shutdown or capacity eviction. | — | 2026-09-20 | `unit + E2E` | [`execution_and_data_flow.md`](architecture/execution_and_data_flow.md), [`persistence.md`](architecture/persistence.md), [`test_inference_api.py`](../../app/tests/e2e/test_inference_api.py) | Provide a deterministic checkpoint/data fixture or run a manual live session covering prediction, bet update, clear, persistence, and shutdown. |
| `persistence.sqlite` | `VALIDATED` | SQLite default database, Alembic initialization, repositories, dataset/inference persistence, and checkpoint references. | Python 3.14 Development reinstall preserved the database at Alembic head; SQLite persistence contract, migration rejection/rollback/concurrency, repository, and ORM tests passed; Alembic head check passed. | Non-empty unversioned databases, schema drift, and unknown revisions intentionally fail closed. | — | 2026-09-21 | `unit + E2E` | [`persistence.md`](architecture/persistence.md), [`test_database_initialization.py`](../../app/tests/unit/test_database_initialization.py), [`test_sqlite_repository_orm.py`](../../app/tests/unit/test_sqlite_repository_orm.py) | Re-run the SQLite contract after model, migration, or repository changes. |
| `persistence.postgresql` | `BLOCKED` | External PostgreSQL schema migration and repository conformance. | The standard suite executed five PostgreSQL tests as `SKIPPED` because `TEST_POSTGRES_URL` was not set; hosted CI defines a PostgreSQL 17 service and runs the conformance suite. A local PostgreSQL service is present, but no isolated test database/URL was configured for this run. | PostgreSQL behavior is not currently proven; SQLite evidence must not be promoted to PostgreSQL evidence. | `ISSUE-002` | 2026-09-20; five conformance tests skipped | `None` | [`persistence.md`](architecture/persistence.md), [`testing_and_quality.md`](coding/testing_and_quality.md), [`test_persistence_contract.py`](../../app/tests/e2e/test_persistence_contract.py), [`ci.yml`](../../.github/workflows/ci.yml) | Run the conformance suite against an explicitly isolated PostgreSQL test database or use a successful hosted CI result, then update this row. |
| `runtime.settings` | `VALIDATED` | Typed `.env` configuration, `runtime-settings.json`, strict updates/reset, JIT capability checks, and live propagation. | Python 3.14.7 settings unit/API tests passed for structured persistence, partial update, reload/reset, supported JIT, and Windows `inductor` rejection; direct `torch.compile` execution also passed. | None evidenced for the supported Python 3.14 contract. | — | 2026-09-21 | `unit + E2E` | [`configuration.md`](runtime/configuration.md), [`test_settings_system.py`](../../app/tests/unit/test_settings_system.py), [`test_settings_api.py`](../../app/tests/e2e/test_settings_api.py) | Re-run settings tests after configuration, capability, or propagation changes. |
| `frontend.workflows` | `PARTIAL` | React/Vite shell, training and inference pages, guidance, settings UI, transport parsing, and desktop-width behavior. | Python 3.14 browser suite covered navigation, page rendering, guidance, settings/JIT persistence, upload/API flows, startup recovery/retry/reload, supported viewport containment, and reduced motion; frontend lint, production build, launcher smoke, and manual waiting-animation inspection passed. | Four live inference-session tests skipped without a checkpoint/data fixture; `ISSUE-003` remains for absent standalone frontend unit/E2E npm scripts; the broader live inference UI still needs a fixture-backed review. | — | 2026-09-21 | `manual + E2E` | [`experience.md`](ui/experience.md), [`components_and_patterns.md`](ui/components_and_patterns.md), [`app_flow.py`](../../app/tests/e2e/test_app_flow.py), [`app/client/README.md`](../../app/client/README.md) | Revalidate the live inference UI and broader visual/accessibility paths after UI changes. |
| `qa.standard-runner` | `VALIDATED` | Repository-standard dependency setup, live services, Python tests, and optional frontend test phases. | `app/tests/run_tests.bat` completed with `Live server phase: PASS`, `Python tests: PASS`, `Frontend bootstrap: PASS`, `Frontend unit tests: SKIPPED`, and `Frontend E2E tests: SKIPPED`; the Python 3.14 run reported `199 passed, 9 skipped, 1 warning in 103.94s`, with frontend lint and production build also passing. | The skipped phases and tests are explicit validation debt, not hidden passes; the warning is a dependency deprecation warning. The canonical pytest cache requires an elevated token on this host because of its existing ACL. | — | 2026-09-21 | `unit + E2E` | [`testing_and_quality.md`](coding/testing_and_quality.md), [`startup.md`](runtime/startup.md), [`run_tests.bat`](../../app/tests/run_tests.bat), [`../QA/python314-migration-validation-20260921.md`](../QA/python314-migration-validation-20260921.md) | Use the supported runner and its canonical cache; investigate any new skip, failure, or warning. |
| `qa.frontend-test-scripts` | `NOT_IMPLEMENTED` | Standalone `test:unit` and `test:e2e` npm scripts for the frontend package. | `app/client/package.json` defines `dev`, `build`, `lint`, and `preview` only; the frontend README and standard runner document the skipped test phases. | Frontend validation relies on backend-hosted Playwright flows, lint, and build rather than an isolated frontend test command. | — | 2026-09-20 | `manual` | [`app/client/README.md`](../../app/client/README.md), [`run_tests.bat`](../../app/tests/run_tests.bat), [`testing_and_quality.md`](coding/testing_and_quality.md) | Decide whether a meaningful standalone frontend test layer is required; if added, wire it into the runner and ledger. |
| `distribution.packaged-artifacts` | `NOT_IMPLEMENTED` | Container, installer, Tauri, MSI, portable executable, and other packaged distribution paths. | Runtime mode and deployment documents explicitly state that the supported boundary is source plus the Windows launcher. | Packaged artifacts are outside the current product scope; do not treat their absence as a broken local web runtime. | — | 2026-09-20 | `manual` | [`modes.md`](runtime/modes.md), [`deployment.md`](runtime/deployment.md) | No action unless product scope changes. |

No external model-provider, authentication, distributed-worker, or cloud-service component is invented in this ledger: the current architecture documents a local layered monolith with process-local training and inference state.

## Open issues

These are the currently actionable problems. Resolved findings are kept below and are not part of the active issue set.

Issue severity uses `CRITICAL`, `HIGH`, `MEDIUM`, and `LOW`; severity is not a functional status.

| Issue ID | Affected Component | Severity | Description | Current Impact | Evidence / Reproduction | Suspected Cause | Blocker | Remediation Status | Required Revalidation | Related Documentation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ISSUE-002` | `persistence.postgresql` | `MEDIUM` | PostgreSQL persistence conformance has no current service-backed result. | The SQLite path can still be assessed independently, but the external database alternative is not currently proven. | `test_persistence_contract.py` skips without `TEST_POSTGRES_URL`; the hosted workflow supplies PostgreSQL 17 instead. | Not inferred; this is an environment-dependent validation requirement. | An explicitly isolated PostgreSQL test database plus `TEST_POSTGRES_URL` and the test dependencies. | Open validation blocker. | Run all PostgreSQL persistence-contract tests and confirm cleanup, migration, rollback, and concurrency behavior. | [`test_persistence_contract.py`](../../app/tests/e2e/test_persistence_contract.py), [`ci.yml`](../../.github/workflows/ci.yml), [`persistence.md`](architecture/persistence.md) |
| `ISSUE-003` | `qa.frontend-test-scripts` and `frontend.workflows` | `LOW` | The frontend package has no standalone unit or E2E npm scripts. | UI changes have no isolated frontend test phase; confidence depends on backend-hosted Playwright flows, lint, build, and manual inspection. | `app/client/package.json` has no `test:unit` or `test:e2e` script, and `run_tests.bat` marks those phases `SKIPPED`. | Not inferred; the package currently defines only its documented scripts. | None; this is a coverage gap, not an unavailable service. | Open validation gap; not a known product defect. | Decide coverage scope; if scripts are added, run them against representative training, inference, settings, and responsive paths. | [`app/client/README.md`](../../app/client/README.md), [`run_tests.bat`](../../app/tests/run_tests.bat), [`experience.md`](ui/experience.md) |

## Validation debt

Validation debt is separate from known defects. It records uncertainty that should guide the next validation pass; it does not imply that the component is broken.

| Component | Current Confidence | Missing Validation | Priority |
| --- | --- | --- | --- |
| `backend.inference` | Medium | A live checkpoint-backed prediction session, bet update, row/context clear, persistence, and shutdown flow. | High |
| `persistence.postgresql` | Low | Service-backed conformance with `TEST_POSTGRES_URL`, including concurrency and cleanup. | Medium |
| `runtime.settings` | Medium | Revalidate PyTorch/`torch.compile` compatibility when the Python or locked ML runtime changes again. | Low |
| `frontend.workflows` | Medium | Live inference interaction plus manual visual/accessibility checks for training, inference, settings, guidance, keyboard behavior, and the documented desktop-width boundary. | High |
| `qa.frontend-test-scripts` | Low | A decision on whether standalone frontend tests are required and, if so, representative scripts. | Medium |
| `runtime.source-release` | Medium | Release-gate evidence for the next version: synchronized metadata, clean ancestry, hosted CI, and annotated tag. | Medium |

## Resolved and historical findings

These entries provide provenance without making obsolete findings look active.

| Finding | Current State | Provenance | Ongoing Relevance |
| --- | --- | --- | --- |
| `HIST-001` — duplicated configuration, contract, lifecycle, and persistence ownership | Resolved in the current architecture; canonical owners are documented and guarded by architecture tests. | [`findings_and_remediation.md`](architecture/findings_and_remediation.md), [`system_overview.md`](architecture/system_overview.md), [`test_architecture_cleanup.py`](../../app/tests/unit/test_architecture_cleanup.py) | Revalidate affected boundaries after API, settings, persistence, or lifecycle changes; do not reopen as an active defect without a regression. |
| `HIST-002` — legacy cache and launcher compatibility paths | Removed from current ownership; `runtimes/cache` and current launcher paths are the supported model. | [`startup.md`](runtime/startup.md), [`windows_automation.md`](coding/windows_automation.md), [`findings_and_remediation.md`](architecture/findings_and_remediation.md) | Recheck cache and process cleanup after launcher changes. |
| `HIST-003` — checkpoint comparison UI and related workflow | Retired before `v3.4.2`; current training workflow documentation no longer presents it as a supported feature. | [`workflows.md`](operations/workflows.md), [`experience.md`](ui/experience.md) | Treat requests to restore it as new scope, not as a broken current capability. |
| `HIST-004` — missing managed runtime after application uninstall | Resolved during this bootstrap by the authorized Development reinstall; the subsequent standard runner completed with `201 passed, 10 skipped`. | [`startup.md`](runtime/startup.md), [`run_tests.bat`](../../app/tests/run_tests.bat) | If the environment is removed again, record it as setup state and restore it before judging product behavior. |

## Revalidation triggers

| Change Area | Revalidate |
| --- | --- |
| `start_on_windows.ps1`, runtime setup, ports, cache, or lifecycle | `application.startup`, `qa.standard-runner`, runtime cache ownership, live readiness, and cleanup. |
| API contracts, Pydantic settings, generated transport types, or route behavior | `backend.api-contracts`, settings, generated contract parity, backend unit tests, and affected browser workflows. |
| Training, worker, checkpoint, or inference services | Training/inference unit and E2E flows, cancellation/resume, persistence, and manual UI behavior. |
| SQLAlchemy models, Alembic revisions, or repositories | SQLite migration/repository contract plus PostgreSQL conformance when the service is available. |
| React pages, components, parsers, styles, or interaction states | Frontend lint/build, relevant Playwright flows, and manual visual/accessibility checks. |
| Version metadata or release preparation | Synchronized package/docs metadata, clean ancestry, hosted CI, annotated tag, and source-release boundary. |

## Evidence and linking policy

The ledger records compact conclusions and links outward. Long debugging narratives, implementation plans, test logs, screenshots, and detailed architecture rationale belong in their dedicated documents or `assets/QA/` evidence artifacts. When a detailed artifact does not exist, the ledger must say so rather than inventing a validation claim.
