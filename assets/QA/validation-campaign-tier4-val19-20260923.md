# VAL-19 Launcher Maintenance Validation

Date: 2026-09-23
Branch: `develop`
Application baseline: `b53984a9e67cab8764fb84245bbe2ef1f1abee94`
Profile: Windows 11 Pro build 26200, PowerShell 7.6.6, managed Python 3.14.7, Node 22.13.0, SQLite 3.50.4, Chromium, CPU, one backend worker.

## Scope and gate review

The canonical ledger had VAL-00 through VAL-17 validated for the supported Windows/SQLite/CPU profile. VAL-19 was the next normal campaign slice. VAL-18 remains a separate CUDA/device/JIT/mixed-precision slice; the available GPU does not replace that validation. VAL-09/20 remain conditional because their dependency triggers did not change in this patch and their acceptance contracts are tracked separately. VAL-21/22 remain later resilience work.

The overall `validation.campaign` remains `PARTIAL`. `frontend.workflows` remains `PARTIAL`; ISSUE-003 remains open because the client has no standalone unit or E2E scripts. `runtime.source-release` remains `WORKING`; packaged artifacts remain outside the source-plus-launcher scope. No gate is currently `BLOCKED`.

## Maintenance actions exercised

The PowerShell harness loaded the current launcher functions and ran them against disposable fixture trees with an isolated `FAIRS_DATA_DIR`. It also checked all six menu dispatch entries.

| Action | Observed result |
| --- | --- |
| Remove logs | Removed root and nested `.log` files under the isolated log root. Preserved nested notes and a `.log` file outside that root. |
| Clear cache | Removed root and nested sentinels under `runtimes/cache`; preserved a neighboring `cache-neighbor` directory and verified the cache environment values were restored. |
| Remove checkpoints | Removed checkpoint contents while preserving `.gitkeep`; database and log files remained unchanged. |
| Remove all data | In external-database mode, removed the local SQLite database, WAL, SHM, and log files. Preserved notes, checkpoints, and an external-database sentinel. |
| Uninstall | Removed the current runtime, cache, backend virtual environment, client `node_modules`, and client `dist`; recreated the runtime marker and preserved `app/server/uv.lock`, `app/client/package-lock.json`, and the user database. |
| Stop application processes | Used live Win32 CIM records for a real test-owned PowerShell parent/child sleeper tree whose command line identified the fixture as an application process. The launcher stopped the selected process tree, including its console-host descendants. An unrelated in-fixture process and an app-shaped process outside the fixture root remained alive until test cleanup. Noninteractive and declined confirmations left the owned tree running. |

For the five file actions, the harness checked both noninteractive and declined confirmations and verified fixture hashes remained unchanged. It then held a real loopback TCP listener on the configured backend port; each action stopped at the application-running guard and left the fixture unchanged. The port guard used the launcher's live `netstat` PID lookup.

## Fix found during validation

Uninstall failed when a directory contained exactly one child. PowerShell returned a scalar `FileInfo`, and appending a second enumerated item raised an `op_Addition` error. `Remove-LauncherPath` now normalizes the enumerated entries to an array before traversal. The uninstall fixture has a one-file `dist` directory and exercises this regression. No API or schema change was needed.

## Verification results

| Check | Result |
| --- | --- |
| Focused launcher contract and maintenance regressions | `11 passed` in 21.14 seconds after the final backend/client lockfile preservation assertions. |
| PowerShell parser | Passed for `start_on_windows.ps1` and `windows_launcher_maintenance.ps1`. |
| Standard Windows runner, final run | `262 passed, 6 skipped` in 482.14 seconds; exit code 0. Live server, Python, and frontend bootstrap phases passed. |
| Standard runner frontend unit and E2E phases | `SKIPPED`; `app/client/package.json` defines neither script. This remains ISSUE-003. |
| `git diff --check` | Passed after ledger/report changes. |

The six pytest skips are five PostgreSQL cases because `TEST_POSTGRES_URL` was not configured, plus the VAL-15 strategy browser case because its transient learned checkpoint was not present in the disposable baseline snapshot. Hosted PostgreSQL conformance is already tracked separately in the ledger. The readiness loop printed Windows timeout input-redirection warnings in redirected execution; both services reached health and the live-server phase passed.

An initial standard-runner attempt used a newly empty data root and produced 15 failures and 2 errors where browser and training tests expected the preloaded dataset/checkpoints. That root was discarded. The final run used a disposable SQLite backup (`PRAGMA integrity_check: ok`, five datasets) plus a copy of the 17 baseline checkpoint directories, so it preserved the repository data while satisfying those fixtures.

## Isolation and cleanup

The runner's browser cache (611 files) and all derived caches used a temporary `STANDARD_TEST_CACHE_ROOT`. Its `FAIRS_DATA_DIR` pointed to the disposable fixture clone. `settings/.env` was restored byte-for-byte with SHA-256 `A421DB30276B690D1AC14549AFCE9E850AF72533B95EBFF6FBC2DB42610EECDE`. Temporary data/cache roots and process-test QA fixtures were removed. Ports 8890 and 8051 were clear after the runner stopped its services. The tracked screenshots regenerated by broad browser tests were restored; no unrelated QA image changes are included.

## Remaining gates and limitations

- VAL-19 is `VALIDATED` for the supported Windows launcher path.
- VAL-18 remains a separate hardware slice. VAL-09/20 remain conditional pending their documented triggers; VAL-21/22 remain open resilience slices.
- ISSUE-003 and `frontend.workflows` remain open/partial. Broader screen-reader, additional-browser, and physical-device checks were not part of VAL-19.
- The source-release gate remains `WORKING`; packaged artifacts remain outside current scope.
- No gate is `BLOCKED`.
