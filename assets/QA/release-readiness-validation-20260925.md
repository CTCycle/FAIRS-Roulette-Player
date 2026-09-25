# Release Readiness Validation — 2026-09-25

Last updated: 2026-09-25

## Release assessment

The implemented Windows source profile is broadly validated. `STARTUP-01` remains partial because the official canonical-cache cold path fails on protected cache residue; the next version and release commit have not been selected or synchronized to `main`, which is a separate release workflow rather than a validation gate.

## Validation ledger disposition

- **Passed:** `VAL-00`–`VAL-08`, `VAL-10`–`VAL-19`, `VAL-21`, and `VAL-22` for their recorded profiles. This pass rechecked the Windows standard runner, the CUDA profile (`VAL-18`), the strategy workflow (`VAL-15`), and malformed inference observations (`VAL-21`).
- **Partial:** `STARTUP-01` and the aggregate `validation.campaign` remain partial because the protected canonical cache prevents a clean official cold-launch dependency run. The alternate-cache startup and live application checks passed.
- **Blocked:** None.
- **Failed:** None remain after fixes and revalidation.
- **Not tested:** None of the registered gates. `VAL-09` and `VAL-20` are not registered gates.
- **Deferred:** None of the pre-release validation gates. Packaged artifacts and release operations remain outside the validation ledger.
- **No separate conditional gates:** The supported Windows JIT behavior is covered by the passed `VAL-18` boundary; no duplicate gate is maintained.

## Current evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Isolated Windows standard runner | 277 Python tests passed, 6 skipped in 265.65s. Live services, frontend build/bootstrap, 11 frontend unit tests, and 4 Chromium browser tests passed; a separate final `npm run lint` also passed. | [Full runner log](release-validation-standard-runner-20260925-isolated.log), [lint log](release-validation-frontend-lint-final-20260925.log) |
| Hosted CI | Run `36134180311` passed backend validation, frontend validation, and PostgreSQL persistence conformance on commit `1032bd56bb9aaa83bb26aef3fa9d2a2de59ad98b`. | [GitHub CI run](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/36134180311) |
| Final inference input boundary | 1 browser test passed on final source. Decimal input is rejected as non-integer; `-1` and `99` receive API 422 responses, retain the entered value, and leave the prediction pending with step count 0 and capital 1000; a valid follow-up outcome advances the session. The same runner invocation passed 11 frontend unit tests and 4 browser tests. | [Focused runner log](release-validation-input-integrity-final-20260925.log) |
| CUDA, mixed precision, and JIT | RTX 3060 Laptop GPU (`cuda:0`); real dataset-5, one-episode job completed with eager JIT and mixed precision. Device selection, invalid device index, CPU mixed-precision rejection, finite metrics, checkpoint publication, persisted flags, and worker log assertions passed. | [Targeted runner log](release-validation-val18-recheck-20260925-final.log); the test also passed in the full runner. |
| Strategy suggestion | The Training wizard produced a real strategy checkpoint from dataset 5. Inference showed the `Martingale` suggestion and €10 amount; applying it left the same step pending with capital 1000 and step count 0. The focused browser regression passed. The clean full-suite data copy did not contain this task-generated fixture, so the suite reports that one test as skipped. | [Targeted runner log](release-validation-val15-recheck-20260925.log), [rendered evidence](val15-strategy-suggestion.png) |
| Rendered desktop workflows | Chrome exercised training-to-inference checkpoint handoff, inference start/prediction/invalid and valid outcomes, Settings save/reload/reset, and the configured roulette pool boundary. The 99 input remained visible and no longer became a false loss; valid recovery succeeded. | [Inference boundary log](release-validation-input-integrity-final-20260925.log), [visual recheck log](release-validation-visual-recheck-20260925-r2.log), [Training screenshot](val17-training-1440x900.png), [Inference history screenshot](val12-inference-history-replay.png) |
| Official cold launcher | The canonical cache path reached frontend `npm ci` but stopped on protected cached tarballs with `EACCES`; the same locked install and live app passed with a task-owned cache. | [Launcher state evidence](launcher-state-validation-20260921.md) |

The six full-suite skips were the five PostgreSQL cases without `TEST_POSTGRES_URL` and the `VAL-15` case without its transient checkpoint fixture. The PostgreSQL conformance job passed in a prior hosted run; hosted CI on the release candidate is still required. `VAL-18` did not skip: CUDA was available and the targeted test passed.

## Fixes made and revalidated

- Inference no longer clamps typed outcomes into the supported roulette range or truncates decimals through `parseInt`. It preserves the entered value, rejects non-integer input in the UI, and lets the API validate integer range. The final browser regression covers decimal, negative, above-range, and valid recovery paths.
- `app/tests/run_tests.bat` now uses delayed expansion when capturing and checking the frontend build exit code inside its parenthesized batch block. The launcher-contract test guards both delayed-expansion expressions, and the standard runner completed all phases successfully.

## Environment integrity

`settings/.env` was temporarily pointed at a disposable data copy because runtime bootstrap intentionally overrides process environment variables from that file. The original file was restored byte-for-byte (SHA-256 `A421DB30276B690D1AC14549AFCE9E850AF72533B95EBFF6FBC2DB42610EECDE`). The canonical SQLite database was restored from its pre-run snapshot (SHA-256 `F139B42B50E1FF21DC460C8AF90472B83149E5EE1A28B499C77D2438A3136B34`); task-created SQLite sidecars and the task-generated strategy checkpoint were removed. No service remains listening on ports 8890 or 8051.

## Remaining validation work

1. Repair the protected canonical cache or add an approved alternate-cache path to the launcher contract, then rerun `STARTUP-01`. The alternate-cache evidence demonstrates the application behavior but does not make the official cold path pass.

Release operations are intentionally outside the validation ledger: a separate future workflow may select the next version, synchronize `main`, run hosted CI on that exact candidate, and create an annotated tag. CI run `36134180311` passed for the current `develop` implementation commit; it does not validate a future versioned release candidate. No release, publish, deploy, tag, or package action was performed here.

The supported distribution is source plus the Windows launcher. Installers, containers, and bundled desktop executables are not implemented and are not part of the documented release scope.
