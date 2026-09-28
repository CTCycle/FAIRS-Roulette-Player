## Project Status Ledger

Last updated: 2026-09-26

## Purpose and authority

This document is the canonical catalog of the current operational state of FAIRS. It summarizes implementation status, meaningful validation evidence, limitations, blockers, historical findings, and required revalidation. Architecture, implementation, test, and remediation documents remain authoritative for their own subjects; this ledger is the authority for cross-cutting status and validation-gate disposition.

The durable conclusions formerly distributed across `assets/QA` reports, logs, screenshots, and fixtures have been synthesized into this ledger. The ignored `assets/QA/` path remains only as a transient output location for local runners and CI; it is not a documentation source and accumulated artifacts must not be treated as current evidence after a run.

The current snapshot includes the Python `3.14.7` managed runtime, PyTorch `2.10.0+cu130`, Node `22.13.0`, SQLite at Alembic head `0002_rename_relative_preference`, the supported Windows/SQLite/CPU profile, the supported desktop browser boundary, hosted PostgreSQL conformance, and one RTX 3060 CUDA profile. The functional campaign gates `VAL-00`–`VAL-08`, `VAL-10`–`VAL-19`, `VAL-21`, and `VAL-22` are passed for their recorded profiles. `STARTUP-01` remains `PARTIAL` because the official cold launcher cannot be observed under the current protected runtime/cache boundary; the prepared runtime, warm launcher, and live application passed. The frontend workflow component remains `PARTIAL` only for spoken screen-reader evidence: DOM, accessibility-tree, keyboard, and visual checks passed, but a user-controlled Windows Narrator/Speech Recap observation is not recorded. No current gate is `FAILED`, `BLOCKED`, or `DEFERRED`.

## Maintenance rules

Future coding agents must:

1. Read this ledger before substantial implementation or validation work.
2. Use it to find known defects, validation boundaries, and previously validated behavior.
3. Update affected entries after implementation changes, meaningful validation, regressions, or blocker changes.
4. Record the exact source revision, environment, scenarios, result, limitation, and follow-up; do not promote a capability from source presence or test definitions alone.
5. Downgrade a status when a current regression is observed.
6. Close or move an issue to the historical section only after remediation and revalidation.
7. Keep one entry per underlying issue and preserve unresolved defects or environment boundaries even when temporary artifacts are removed.
8. Keep this ledger synchronized with the actual repository, source tests, and hosted evidence.

## Status taxonomy

| Status | Meaning |
| --- | --- |
| `VALIDATED` | Implemented and confirmed through meaningful current testing or manual validation. |
| `WORKING` | Believed to work from implementation and limited or indirect evidence, but not fully validated. |
| `PARTIAL` | Implemented, but incomplete, degraded, or valid for only part of the expected behavior. |
| `BROKEN` | Known not to work correctly. |
| `BLOCKED` | Cannot currently be validated or completed because an external dependency, service, credential, hardware constraint, or similar blocker is unavailable. |
| `UNVALIDATED` | Implementation exists, but current evidence is insufficient to claim that it works. |
| `UNKNOWN` | The capability is present or intended, but available evidence is too limited to establish a meaningful partial result. |
| `NOT_IMPLEMENTED` | The expected capability is absent from this checkout. |
| `DEPRECATED` | Retained only for compatibility or scheduled for removal. |

### Gate disposition used for the release-readiness audit

| Disposition | Meaning |
| --- | --- |
| `PASSED` | The recorded acceptance scenarios were executed with current or still-valid evidence at the tested implementation revision. |
| `PARTIAL` | The implementation or an alternate validation path is covered, but a scoped acceptance path remains incomplete. |
| `BLOCKED` | A scoped acceptance path cannot currently be observed because an external environment, hardware, or user-controlled dependency is unavailable. |
| `FAILED` | Current execution reproduced an application defect or an acceptance assertion failed without an accepted product explanation. |
| `NOT TESTED` | The gate is registered, relevant, and lacks meaningful execution evidence. |
| `DEFERRED` | The gate is intentionally outside the current pre-release scope for a documented reason; it is not used to hide an actionable failure. |

`VALIDATED` component rows map to `PASSED` only where their evidence remains applicable to the current implementation. Release operations, version selection, branch synchronization, hosted CI for a future candidate, tag creation, and packaged artifacts are scope boundaries rather than validation gates. `Validation Level` uses `None`, `unit`, `integration`, `E2E`, `manual`, or a combination. The existence of a test does not change `None` into evidence.

## Current status summary

| Status | Components in this snapshot |
| --- | --- |
| `VALIDATED` | `docs.ontology`, `application.startup`, `backend.api-contracts`, `backend.training`, `backend.inference`, `persistence.sqlite`, `persistence.postgresql`, `runtime.settings`, `qa.standard-runner`, `qa.frontend-test-scripts` |
| `WORKING` | `runtime.source-release` |
| `PARTIAL` | `frontend.workflows`, `validation.campaign` |
| `BROKEN` | None evidenced in the current checkout. |
| `BLOCKED` | None. |
| `UNVALIDATED` | None current; remaining uncertainty is recorded as `PARTIAL` or validation debt. |
| `NOT_IMPLEMENTED` | `distribution.packaged-artifacts` |
| `DEPRECATED` | None current. |

## Current component ledger

| Component | Status | Scope | Current evidence and limitation | Last validated | Validation level | Related docs | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `docs.ontology` | `VALIDATED` | Root index, lower-case topic branches, dated leaf documents, and ledger discoverability. | The complete `assets/docs/` tree, naming rules, and post-consolidation links were inspected. | 2026-09-26 | `manual` | [`project_index.md`](project_index.md) | Update the index and ledger together when document roles or state evidence change. |
| `runtime.source-release` | `WORKING` | Source-only distribution boundary and current application version; a release-operation boundary, not a validation gate. | `v3.5.0` is recorded in package metadata, locks, README, and deployment docs. Candidate CI passed on the exact candidate; synchronized `develop`/`main`, annotated tag, and the GitHub source release later completed at `b7000413b071c263c4314b2e515aa570a5031018`. No installer, container, desktop package, or bundled executable is supported. | 2026-09-26 | `manual` | [`deployment.md`](runtime/deployment.md), [`modes.md`](runtime/modes.md), [GitHub release v3.5.0](https://github.com/CTCycle/FAIRS-Roulette-Player/releases/tag/v3.5.0) | Repeat candidate lock, CI, synchronization, tag, and source-release checks for the next version. |
| `application.startup` | `VALIDATED` | Windows launcher preparation, configured-port guardrails, dependency/build state, database startup, backend health, frontend readiness, single-worker lifecycle, and stop behavior. | Warm option 1, rendered `/training` with `Connected`, grouped port conflicts, decline/confirmation/noninteractive fail-closed behavior, content fingerprints, state publication, four TestClient lifespan cycles, and focused current unit/lint/build checks passed. The official cold path remains environment-limited by protected `python314._pth` and canonical cache residue; alternate-cache/live-app evidence passed without changing protected content. | 2026-09-26 | `manual + E2E` | [`startup.md`](runtime/startup.md), [`deployment.md`](runtime/deployment.md), [`test_windows_launcher_contract.py`](../../app/tests/unit/test_windows_launcher_contract.py), [`run_tests.bat`](../../app/tests/run_tests.bat) | Re-run warm/cold startup, port, state/fingerprint, browser-readiness, and cleanup checks after launcher or bootstrap changes. |
| `backend.api-contracts` | `VALIDATED` | FastAPI routers, Pydantic contracts, health/system, upload, training, inference, settings, and generated frontend transport types. | Live OpenAPI exposed 24 paths and 42 schemas; generated transport parity, route regressions, and all live inference-session routes passed. | 2026-09-22 | `unit + E2E` | [`backend_api.md`](architecture/backend_api.md), [`execution_and_data_flow.md`](architecture/execution_and_data_flow.md), [`test_generated_contracts.py`](../../app/tests/unit/test_generated_contracts.py), [`test_inference_api.py`](../../app/tests/e2e/test_inference_api.py) | Re-run contract and affected route slices after API or schema changes. |
| `backend.training` | `VALIDATED` | Dataset preparation, validation/start/status/stop/resume, workers, metrics, and checkpoint production for Windows/SQLite/CPU. | Real stored-data telemetry and checkpoint publication, deterministic cancellation/concurrency, resume byte preservation and lineage, fresh validation-metric provenance, Training-to-Inference handoff, spawned-worker bootstrap, and current resilience cycles passed. Earlier broad-run checkpoint/recovery failures were not reproduced by later seeded standard runs. | 2026-09-24 | `unit + E2E + manual` | [`execution_and_data_flow.md`](architecture/execution_and_data_flow.md), [`workflows.md`](operations/workflows.md), [`test_training_api.py`](../../app/tests/e2e/test_training_api.py), [`test_training_service.py`](../../app/tests/unit/test_training_service.py) | Re-run worker-path, cancellation, resume, provenance, and checkpoint checks after training/runtime changes; repeat CUDA checks after ML-runtime or hardware changes. |
| `backend.inference` | `VALIDATED` | Checkpoint-backed sessions, prediction/bet loop, strategies, replay correction/removal, rollback, reload/restart recovery, persistence, clearing, and shutdown. | VAL-11–15 and the current resilience recheck passed with visible/persisted state agreement, process-local session expiry after restart, candidate rollback audit retention, and pending suggested-bet application. Model objects are intentionally not reconstructed after restart or capacity eviction; ended history is retained. | 2026-09-24 | `unit + E2E + manual` | [`execution_and_data_flow.md`](architecture/execution_and_data_flow.md), [`persistence.md`](architecture/persistence.md), [`test_inference_api.py`](../../app/tests/e2e/test_inference_api.py), [`test_inference_strategy.py`](../../app/tests/e2e/test_inference_strategy.py) | Re-run lifecycle, replay, rollback, restart, strategy, and capacity checks after inference or persistence changes. |
| `persistence.sqlite` | `VALIDATED` | SQLite initialization, Alembic migrations, repositories, dataset/inference persistence, and checkpoint references. | Fail-closed migration, rollback, concurrency, repository/cascade, restart persistence, deletion persistence, at-head no-op, integrity, and isolated cleanup checks passed. Non-empty unversioned databases, schema drift, and unknown revisions intentionally fail closed. | 2026-09-24 | `unit + E2E + manual` | [`persistence.md`](architecture/persistence.md), [`test_database_initialization.py`](../../app/tests/unit/test_database_initialization.py), [`test_sqlite_repository_orm.py`](../../app/tests/unit/test_sqlite_repository_orm.py) | Re-run the SQLite contract after model, migration, or repository changes. |
| `persistence.postgresql` | `VALIDATED` | PostgreSQL migration and repository conformance using the hosted service. | Hosted PostgreSQL 17.11 conformance job `107244752370` in CI run `35879722209` passed. Local runs skip five cases without `TEST_POSTGRES_URL`; that is a coverage boundary, not a current defect. | 2026-09-23 | `integration` | [`persistence.md`](architecture/persistence.md), [`test_persistence_contract.py`](../../app/tests/e2e/test_persistence_contract.py), [`ci.yml`](../../.github/workflows/ci.yml), [hosted job](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/35879722209/job/107244752370) | Re-run hosted or configured-local PostgreSQL conformance after schema or repository changes. |
| `runtime.settings` | `VALIDATED` | Typed environment configuration, `runtime-settings.json`, strict update/reset, JIT capability checks, and live propagation. | Browser save/reload/reset and invalid-range flows, CPU `eager` compilation, Windows `inductor` rejection, propagation rollback, CUDA/mixed precision, ten repeated save/read/reset cycles, and complete-default restoration passed. | 2026-09-24 | `unit + E2E` | [`configuration.md`](runtime/configuration.md), [`test_settings_system.py`](../../app/tests/unit/test_settings_system.py), [`test_settings_api.py`](../../app/tests/e2e/test_settings_api.py) | Re-run settings and capability checks after configuration, compiler, or propagation changes. |
| `frontend.workflows` | `PARTIAL` | React/Vite shell, Training and Inference workflows, guidance, Settings, transport parsing, and supported desktop widths. | Guidance accessibility, reduced motion, visual desktop routes, active states, checkpoint handoff, invalid/valid inference recovery, Settings feedback, and Chromium/Edge 1100px/1099px behavior passed. DOM roles and accessibility-tree semantics are not spoken-output proof; Windows Narrator/Speech Recap observation of save/reset, validation-error, and recovery feedback remains unrecorded. Phone/mobile layouts are outside the supported desktop specification. | 2026-09-25 | `manual + E2E + unit` | [`experience.md`](ui/experience.md), [`components_and_patterns.md`](ui/components_and_patterns.md), [`app/client/README.md`](../../app/client/README.md), [`frontend.spec.ts`](../../app/client/tests/e2e/frontend.spec.ts) | Capture a user-controlled Windows Narrator/Speech Recap session for the feedback and recovery paths, then rerun lint, build, and affected rendered workflows after frontend changes. |
| `qa.standard-runner` | `VALIDATED` | Repository-standard dependency setup, live services, Python tests, and frontend phases. | The isolated current runner passed 277 Python tests with 6 documented skips, live services, frontend build/bootstrap, 11 frontend unit tests, and 4 Chromium browser tests; focused input, strategy, CUDA, visual, and lint reruns passed. Hosted candidate CI run `36235856482` passed backend, frontend, and PostgreSQL jobs. | 2026-09-26 | `unit + E2E` | [`testing_and_quality.md`](coding/testing_and_quality.md), [`startup.md`](runtime/startup.md), [`run_tests.bat`](../../app/tests/run_tests.bat), [`ci.yml`](../../.github/workflows/ci.yml) | Keep standard runs on a seeded disposable data root and isolated caches; distinguish local PostgreSQL/fixture skips from product failures. |
| `validation.campaign` | `PARTIAL` | Tiered validation of the Windows source profile plus SQLite/CPU, PostgreSQL, CUDA, maintenance, frontend, and resilience boundaries. | All registered `VAL-*` functional gates are passed for their recorded profiles. `STARTUP-01` remains partial because this execution identity cannot rewrite the protected portable-runtime file or canonical cache residue. A 2026-09-26 runner retry stopped before tests at offline PyPI dependency resolution and does not change application status. | 2026-09-26 | `manual + E2E + unit + integration` | [`testing_and_quality.md`](coding/testing_and_quality.md), [`startup.md`](runtime/startup.md), [`workflows.md`](operations/workflows.md), [`findings_and_remediation.md`](architecture/findings_and_remediation.md) | Repair the protected runtime/cache boundary or provide an approved alternate-cache launcher path, then rerun `STARTUP-01`. |
| `qa.frontend-test-scripts` | `VALIDATED` | Client-owned unit and deterministic mocked browser tests for representative workflows and the supported desktop boundary. | Vitest passed 11 tests across 3 files; mocked Playwright passed 4 Chromium and 4 Edge cases; the scripts are wired into the Windows runner and frontend CI. `ISSUE-003` is closed. Mocked API coverage does not replace live backend lifecycle coverage. | 2026-09-25 | `unit + E2E` | [`package.json`](../../app/client/package.json), [`tests/unit`](../../app/client/tests/unit), [`frontend.spec.ts`](../../app/client/tests/e2e/frontend.spec.ts), [`run_tests.bat`](../../app/tests/run_tests.bat), [`ci.yml`](../../.github/workflows/ci.yml) | Re-run the scripts after payload, parser, session-storage, or covered workflow changes. |
| `distribution.packaged-artifacts` | `NOT_IMPLEMENTED` | Container, installer, Tauri, MSI, portable executable, and other packaged distribution paths. | The supported distribution is source plus the Windows launcher. Absence of packaged artifacts is an explicit scope boundary, not a broken local web runtime. | 2026-09-20 | `manual` | [`modes.md`](runtime/modes.md), [`deployment.md`](runtime/deployment.md) | No action unless product scope changes. |

No external model-provider, authentication, distributed-worker, or cloud-service component is invented in this ledger: the current architecture is a local layered monolith with process-local training and inference state.

## Comprehensive validation campaign

The campaign follows the dependency chain `startup → persistence/settings → datasets → training → checkpoint → inference` and the execution loop `Inspect → Execute → Observe → Diagnose → Fix → Retest → Regress → Record`. The core profile is Windows, managed Python `3.14.7`, SQLite, CPU, one backend worker, and the supported desktop boundary. Browser evidence requires rendered state plus console/network observation; persistence/model evidence includes database, dataset, checkpoint, session, or job identity.

### Ordered slice register

| Tier | Slice IDs | Current result | Scope and meaningful evidence |
| --- | --- | --- | --- |
| 0 — Environment and startup | `VAL-00`, `VAL-01` | `PASSED` | Established dataset `5` with 120 rows, real CPU job `fae03fc4`, checkpoint `val00_lineage_20260921`, SQLite head, health, frontend-first startup, full-green zero rotor sector, browser readiness, owned shutdown, and clear ports. |
| 1 — Foundations | `VAL-02`–`VAL-06` | `PASSED` | Routes and 1100/1099 desktop boundary, live OpenAPI/generated contracts, settings persistence and CPU `eager`, SQLite migration/repository/restart behavior, dataset import/delimiters/protected deletion, and two fixed product defects. |
| 2 — Core training | `VAL-07`, `VAL-08`, `VAL-10` | `PASSED` | Six-step wizard/resource preflight, real stored-data telemetry/checkpoint publication, cancellation/concurrency, resume safety and provenance, and Training-to-Inference handoff. |
| 3 — Inference | `VAL-11`–`VAL-15` | `PASSED` | Live session lifecycle, replay correction/removal, failed-replacement rollback, browser reload/backend restart recovery, and real strategy suggestion application. |
| 4 — Cross-cutting and advanced | `VAL-16`–`VAL-19` | `PASSED` | Guidance keyboard/focus/reduced motion, rendered desktop views and active states, hosted PostgreSQL, one RTX 3060 CUDA/eager-JIT/mixed-precision profile, and all launcher maintenance actions. |
| 5 — Resilience and boundaries | `VAL-21`, `VAL-22` | `PASSED` | Malformed-input and state-preserving recovery, repeated lifecycles, capacity/telemetry bounds, cleanup, settings repetition, and state-leak checks. |
| 6 — Startup follow-up | `STARTUP-01` | `PARTIAL` | Warm/alternate-cache startup and live application passed; official cold dependency/runtime preparation remains unobservable because protected `_pth` and canonical cache content cannot be changed by this execution identity. |

### Current gate register

| Gate | Disposition | Evidence, observation, limitation, or follow-up |
| --- | --- | --- |
| `VAL-00` | `PASSED` | Exact Windows/Python 3.14.7/SQLite/CPU baseline, real 120-row upload, job `fae03fc4`, completed checkpoint, metadata, and clean initial inference state. |
| `VAL-01` | `PASSED` | Official warm startup, health-gated browser transition, port ownership, full-green zero sector, and supported elevated shutdown passed; cold-launch limitation is tracked only under `STARTUP-01`. |
| `VAL-02` | `PASSED` | Eight focused browser tests covered routes, 1100px support, 1099px notice, and two-column Inference layout. The original file screenshot call failed, but in-app visual inspection and assertions passed; later VAL-17 and Chromium/Edge captures supply current visual coverage. |
| `VAL-03` | `PASSED` | Live OpenAPI reported 24 paths/42 schemas, generated transport parity passed, and three contract/architecture tests passed. Direct script invocation had a `sys.path` error; module invocation passed and no product defect existed. |
| `VAL-04` | `PASSED` | Settings save/reload/reset, invalid no-PATCH cases, 422 behavior, propagation rollback, CPU `torch.compile(..., eager)`, and 52 final focused tests passed without warnings after the deprecated constant was replaced. |
| `VAL-05` | `PASSED` | SQLite migration fail-closed/rollback/concurrency, repository/cascade, live restart persistence/deletion, and at-head no-op passed (`37 passed, 5 skipped`). Local PostgreSQL skips are tracked separately. |
| `VAL-06` | `PASSED` | API edge cases, real XLSX, comma/semicolon/tab/pipe browser uploads, protected `409`, refresh/navigation persistence, and cleanup passed. Dataset-list error rendering and tab-separator normalization were fixed and retested. |
| `VAL-07` | `PASSED` | All six wizard sections, dependent controls, stored/generator mapping, semantic validation, validate-before-start ordering, stale/deleted resource preflight, and summary values passed. `VAL07-001` and `VAL07-002` were fixed with API, service, and browser regressions. |
| `VAL-08` | `PASSED` | Current-revision browser run observed exact jobs `b5bee220` and `3d0a363c`, live telemetry, finite terminal metrics, complete checkpoint payload, metadata, refresh, and cleanup. The initial terminal-metric projection defect was fixed before the current pass. |
| `VAL-10` | `PASSED` | Active duplicate start/resume rejection, stop and DELETE cancellation, staged-output cleanup, byte-identical cancelled resume, +2-episode lineage, fresh validation metrics, and handoff provenance passed. One unrelated Settings ACL failure in a broad run was not a VAL-10 defect. |
| `VAL-11` | `PASSED` | Fixed checkpoint/dataset live prediction and manual bet loop, persisted history, row/context clear, active-clear conflict, shutdown, and isolated SQLite audit passed. The baseline checkpoint had no suggested-bet value, so that control was intentionally not promoted by this gate. |
| `VAL-12` | `PASSED` | Correction and row-removal replay preserved visible/persisted rows, rewards, capital, pending prediction, prior-session closure, and preserve-session headers. A historical broad runner had three training failures and two setup errors; later seeded standard validation did not reproduce them. |
| `VAL-13` | `PASSED` | Injected replacement failure left the original session active and usable, closed the candidate while retaining partial audit steps, and restored committed UI values. The stale optimistic UI state exposed by the test was fixed and rerun. |
| `VAL-14` | `PASSED` | Browser reload restored a live session; backend restart expired only process-local model state with the expected `404`, retained ended SQLite history/steps, cleared stale browser state, and allowed a fresh session. Standard runner: `254 passed, 5 skipped`. |
| `VAL-15` | `PASSED` | Real strategy checkpoint produced a visible DAlembert suggestion; the later UI recheck produced Martingale. Applying either suggestion kept the pending step, capital `1000`, and step count `0`. Spawned-worker runtime bootstrap and cleanup-race regressions passed. |
| `VAL-16` | `PASSED` | Training/Inference Help and walkthrough dialogs passed accessible naming, focus containment/return, Escape dismissal, persistence, and reduced-motion checks. A Next→Back focus defect was fixed in `GuidedTour`. This gate records DOM/keyboard/visual accessibility checks and makes no spoken Narrator/Speech Recap claim. |
| `VAL-17` | `PASSED` | Training, Inference, and Settings rendered at 1440×900 and 1100×800; 1099px showed the minimum-width notice; setup/summary/active states and no-overflow/browser-error checks passed. The wizard overlay clipping defect was fixed by portaling to `document.body`. |
| `VAL-18` | `PASSED` | One RTX 3060 Laptop GPU (`cuda:0`) passed device selection/rejection, CPU mixed-precision rejection, `eager` JIT, real dataset-5 CUDA/mixed-precision training, finite metrics, complete checkpoint, and persisted flags. Windows `inductor` remains intentionally rejected; no multi-GPU/performance claim is made. |
| `VAL-19` | `PASSED` | All six maintenance actions, confirmation/port guards, preservation rules, and real process-tree cleanup passed. A one-child `FileInfo` enumeration bug was fixed. |
| `VAL-21` | `PASSED` | Malformed settings/training/upload/inference requests returned deterministic `4xx` responses, preserved persisted/live state, recovered valid operations, and maintained health. Focused five-case and current-tree 16-case runs passed; the first upload `ECONNRESET` was not reproduced and final over-limit responses were `413`. |
| `VAL-22` | `PASSED` | Four lifespan cycles, nine current recheck inference sessions, 18 starts under a 16-session bound, three training cancel/recovery cycles (max 19.076s), 2,001→2,000 telemetry points, four manager cleanups, and ten settings reset cycles passed with no remaining acceptance gap in the tested profile. |
| `STARTUP-01` | `PARTIAL` | The official cold launcher still attempts to rewrite protected `runtimes/python/python314._pth` and protected canonical cache residue prevents a clean cold dependency path. Warm/alternate-cache startup and live rendering passed; rerun after the owner repairs permissions or provides an approved alternate-cache path. |

`VAL-09` and `VAL-20` appeared in older QA notes as conditional names, but no trigger or acceptance contract is registered in the checked-in campaign. They are not missing results, `NOT TESTED` gates, or deferred gates. No registered gate is currently `FAILED`, `BLOCKED`, or `DEFERRED`.

### Release-readiness audit — current checkout

The 2026-09-25/26 release checks passed lock consistency, focused unit coverage, frontend lint, production build, the isolated standard runner, frontend unit/mocked browser coverage, hosted CI, and the approved current Inference figure. Candidate CI run `36235856482` passed for candidate commit `306576036ba0a71d880966dc442c993027b9660d`; release-operation CI run `36235992990` later passed for `b7000413b071c263c4314b2e515aa570a5031018`, which is the published `v3.5.0` tag/release commit. A retry in this execution environment could not resolve `hatchling` from PyPI before tests; it is recorded as an environment limit and does not replace the passing isolated evidence. Release operations are separate from gate disposition.

### Supporting campaign history

These named campaigns supplied evidence to the gate register but are no longer maintained as standalone reports:

| Campaign | Consolidated conclusion |
| --- | --- |
| 2026-09-20 startup launch smoke | Warm option 1 rendered `/training` with `Connected`, six startup checks passed, the local suite passed with documented skips, and owned ports were clear. The canonical dependency path's cache permission failure is superseded by `STARTUP-01`. |
| 2026-09-21 Python 3.14 migration | The managed Python `3.14.7`/PyTorch `2.10.0+cu130` environment, recreated venv, build, warm launch, and prepared-runtime smoke passed. Canonical cache ACL and unexecuted frontend/live-fixture phases remain historical environment boundaries, not current application failures. |
| 2026-09-21 launcher-state validation | Launcher contracts, fingerprints, grouped port guards, fail-closed cancellation, warm launch, and the isolated runner passed. Performance medians and cross-context replacement-listener measurements were not collected and are non-gating validation debt. |
| 2026-09-25 frontend validation | Vitest passed 11 client tests; mocked Chromium and Edge cases passed; runner/CI wiring passed; `ISSUE-003` is closed. This complements, rather than replaces, live backend browser gates. |
| Tier 6 accessibility follow-up | Settings feedback semantics, visible states, and accessibility-tree checks passed. A user-controlled Windows Narrator/Speech Recap observation was not captured, so spoken feedback remains `PARTIAL` and is not promoted from DOM or visual evidence. |
| 2026-09-25/26 release readiness | Candidate lock/build/test/CI evidence and subsequent `v3.5.0` release operations passed. The official cold-launch retry that stopped at offline PyPI resolution remains an environment-limited attempt and does not change the isolated pass or `STARTUP-01` disposition. |

### Historical failure and partial-state reconciliation

| Historical observation | Classification and current authority |
| --- | --- |
| First VAL-08 browser run showed terminal loss/RMSE as `N/A` despite worker metrics. | Product defect `VAL08-001`; terminal projection was fixed and the current-revision browser workflow published finite metrics. Historical failure is retained for provenance, not current status. |
| VAL-12/13 broad runs reported three training failures and two resume setup errors. | Protected-cache/fixture publication and recovery setup boundary; later seeded VAL-14/standard runs passed and no current training defect was reproduced. |
| VAL-18 first two attempts did not run the GPU scenario because repository dotenv overrode the process data root. | Setup/isolation failure; corrected dotenv setup produced the passing CUDA/eager-JIT result. |
| VAL-19 first standard run used an empty data root and produced 15 failures/2 errors. | Invalid fixture baseline; the run was discarded, a seeded integrity-checked clone was used, and the final runner passed. |
| Early Tier 5 recheck had one upload connection reset and a reset assertion that omitted roulette defaults. | Transient transport/assertion findings; the assertion was corrected, isolated upload retry and final focused/current runner passed, and no product defect was established. |
| Older Tier 4/Tier 5 reports said frontend scripts were absent and frontend phases were skipped. | Historical `ISSUE-003`; Vitest and mocked Playwright scripts were added, wired into runner/CI, passed in Chromium and Edge, and the issue is closed. Older skips remain historical revision evidence only. |
| Initial VAL-02 file screenshot capture failed; several launcher cleanup attempts returned Windows access denied. | Harness/host boundaries, not product failures. In-app rendered inspection and browser assertions passed; exact owned process cleanup and clear-port checks passed with the required host permission. |
| 2026-09-26 standard-runner retry stopped at offline PyPI resolution. | Environment-limited attempt before application tests; it does not downgrade the current isolated runner or hosted CI evidence. |

## Open issues

No active application defect is evidenced in the current checkout. `STARTUP-01` is an environment permission boundary and remains tracked as `PARTIAL`, not as a product issue.

## Validation debt

Validation debt records uncertainty or scope boundaries; it does not imply that the component is broken.

| Component | Current confidence | Missing validation or limitation | Priority |
| --- | --- | --- | --- |
| `validation.campaign` | Medium | Official canonical-cache cold launcher remains partial; the same locked dependencies and live application passed with an isolated task-owned cache. | Medium |
| `runtime.settings` | Medium | Revalidate PyTorch/`torch.compile` compatibility when the Python or locked ML runtime changes. | Low |
| `frontend.workflows` | Medium | Supported desktop workflow is covered in Chromium and Edge; phone/mobile layouts are outside the documented product specification, and spoken Settings/error/recovery feedback still needs user-controlled Windows Narrator/Speech Recap observation. | Medium |
| `runtime.source-release` | Medium | The `v3.5.0` source release is complete; repeat the synchronized candidate/tag/release workflow for future versions. | Medium |
| `VAL-18` profile | Medium | Evidence covers one RTX 3060 and the Windows `eager` path only; no multi-GPU, other-driver, cross-device, or performance comparison was run. | Low |

## Resolved and historical findings

These entries provide provenance without making obsolete findings look active.

| Finding | Current state | Ongoing relevance |
| --- | --- | --- |
| `HIST-001` — duplicated configuration, contract, lifecycle, and persistence ownership | Resolved; canonical owners are documented and guarded by architecture tests. | Revalidate affected boundaries after API, settings, persistence, or lifecycle changes. |
| `HIST-002` — legacy cache and launcher compatibility paths | Removed; `runtimes/cache` and current launcher paths are the supported model. | Recheck cache/process cleanup after launcher changes. |
| `HIST-003` — checkpoint comparison UI and related workflow | Retired before `v3.4.2`; not a current capability. | Treat restoration as new scope. |
| `HIST-004` — missing managed runtime after uninstall | Resolved by the authorized Development reinstall; the standard runner subsequently completed. | Restore setup state before judging product behavior if the environment is removed again. |
| `HIST-005` — non-elevated launcher stop permission boundary | Resolved as a host boundary; exact owned processes were stopped with the supported elevated path and ports were clear. | Preserve process identity and permission context during launcher revalidation. |
| `HIST-006` — backend-wait zero rendered as a rectangular green card | Resolved by the full green rotor sector and focused startup regression. | Re-run startup visual/browser checks after wheel or startup-style changes. |
| `HIST-007` — `ISSUE-002` PostgreSQL conformance blocker | Closed by hosted PostgreSQL 17.11 CI conformance on 2026-09-23. | Revalidate after schema, migration, or repository changes; local tests may still skip without a URL. |
| `HIST-008` — Windows-only launcher harness ran on Linux | Resolved by platform-aware skipping on final source/test revision; hosted CI and Windows dynamic harness passed. | Keep static launcher contracts cross-platform and dynamic maintenance tests on Windows. |
| `HIST-009` — `ISSUE-003` frontend test-script gap | Closed on 2026-09-25 by client-owned Vitest/mocked Playwright scripts, runner/CI integration, and Chromium/Edge validation. | Keep the isolated frontend suite current; live backend lifecycle coverage remains in Python Playwright tests. |
| `VAL07-002` — training preflight omitted persisted-resource checks | Resolved by shared preflight for `/training/validate` and `/training/start`; stale/wrong-kind datasets and reused checkpoint names now reject before job creation. | Revalidate when resource lookup or checkpoint creation changes. |

## Revalidation triggers

| Change area | Revalidate |
| --- | --- |
| `start_on_windows.ps1`, runtime setup, ports, cache, or lifecycle | `application.startup`, `qa.standard-runner`, `STARTUP-01`, live readiness, and cleanup. |
| API contracts, Pydantic settings, generated transport types, or route behavior | `backend.api-contracts`, settings, generated parity, backend unit tests, and affected browser workflows. |
| Training, worker, checkpoint, or inference services | Training/inference unit and E2E flows, cancellation/resume, persistence, and manual UI behavior. |
| SQLAlchemy models, Alembic revisions, or repositories | SQLite migration/repository contract plus hosted PostgreSQL conformance when the service is available. |
| React pages, components, parsers, styles, or interaction states | Frontend lint/build, client unit/mocked browser cases, relevant live Playwright flows, and manual visual/accessibility checks. |
| Version metadata or release preparation | Synchronized package/docs metadata, clean ancestry, hosted CI on the exact candidate, annotated tag, and source-release boundary. |

## Evidence and linking policy

The ledger records portable conclusions, exact revisions, meaningful counts, limitations, historical contradictions, and follow-up. Long raw logs, repeated screenshots, disposable databases/checkpoints, browser traces, and temporary caches are not durable documentation. Current evidence should point to source tests, implementation docs, hosted CI, or the approved product figure; transient runner output may be generated under the ignored `assets/QA/` path and should be removed or regenerated rather than linked as a source of truth. Browser roles, accessibility-tree text, and visible feedback do not prove spoken screen-reader output; record a user-controlled Narrator/Speech Recap observation separately. When a detailed artifact is retired, its unique defect, limitation, result, and provenance must remain represented here.
