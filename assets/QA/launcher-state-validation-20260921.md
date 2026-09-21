# Launcher state and port-guardrail validation

Last updated: 2026-09-21

## Revision and scope

- Checkout: `develop`, revision `84b7990` plus the working tree launcher/documentation/test changes.
- Scope: grouped configured-port conflicts, fail-closed cancellation, runtime-probe reuse, independent dependency state, content-based frontend freshness, official warm launch, and rendered browser readiness.

## Results

- PowerShell parser: PASS.
- Launcher contract plus architecture tests: `10 passed`.
- Frontend lint: PASS.
- Frontend production build: PASS.
- Generated state flow: successful `uv sync` and `npm ci` produced the backend and frontend install-state files; the frontend build produced `dist/.fairs-build-state.json`; all three readiness checks returned true.
- Fingerprint behavior: timestamp-only change remained current; a reversible content-byte change made the build stale.
- Port resolver: free ports continued; one process owning both configured test ports produced one record with both ports; decline returned false and left both listeners; confirmation stopped the one PID and cleared both ports; noninteractive conflict failed closed and left the listener alive.
- Full live Python suite under a fresh repository-local cache: `208 passed, 8 skipped, 1 warning`.
- Official option 1 warm launch: backend sync, frontend sync, and frontend build were all skipped; the launcher reported frontend readiness and the real Chrome tab rendered `/training` with `Connected` visible.
- Final port/process check: configured ports `8890` and `8051` were clear after cleanup.

## Validation boundary

The canonical `cmd /c app\\tests\\run_tests.bat` entry point was attempted but stopped during its dependency phase because the pre-existing `runtimes/cache/uv` directory returned Windows access denied. The full live suite was rerun with an isolated repository-local cache without deleting or altering that protected cache. Five-run before/after startup medians were not collected, so this change claims launcher probe deduplication and warm-path behavior, not a quantified end-to-end performance improvement. Replacement-listener and cross-security-context access-denied scenarios remain environment-bound follow-up checks.
