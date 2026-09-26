# Release Readiness Validation — 2026-09-26

Last updated: 2026-09-26

## Release assessment

The next source-release candidate is `v3.5.0`, selected as a minor version because the unreleased change set after `v3.4.2` contains substantial runtime, frontend, API, and validation work. The candidate is ready for the remaining release-operation checks after the validation evidence below; the release operation itself is not a validation gate. Hosted candidate CI has now passed for commit `306576036ba0a71d880966dc442c993027b9660d`.

The registered application gates remain complete for their documented profiles: `VAL-00`–`VAL-08`, `VAL-10`–`VAL-19`, `VAL-21`, and `VAL-22` are passed. `STARTUP-01` remains `PARTIAL` only because the official cold launcher cannot be observed under the current protected local runtime boundary. No application defect was reproduced.

## Candidate evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Dependency lock consistency | **PASS** | `uv lock --check --offline` passed with an isolated candidate cache. |
| Python unit coverage | **PASS** | 173 unit tests passed using the prepared `app/server/.venv`, pytest cache provider disabled, and an isolated temporary root. The Windows launcher-maintenance test passed separately once with host-level permissions: 174 focused unit tests passed in total. |
| Frontend lint | **PASS** | `npm run lint` passed with the repository Node runtime. |
| Production frontend build | **PASS** | `npm run build` passed: TypeScript build and Vite production build completed. The configured TypeScript/Vite cache is protected from the sandbox identity, so this check used the host-level execution path. |
| Existing full validation campaign | **PASS, evidence retained** | The current implementation tree before release-only metadata/image edits passed the isolated standard runner with 277 Python tests, 6 documented skips, live services, frontend build/bootstrap, 11 frontend unit tests, and 4 Chromium cases; hosted CI run `36134180311` passed backend, frontend, and PostgreSQL jobs. See [`release-readiness-validation-20260925.md`](release-readiness-validation-20260925.md). |
| Hosted CI on exact candidate | **PASS** | Run [`36235856482`](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/36235856482) passed backend validation, frontend validation, and PostgreSQL persistence conformance for candidate commit `306576036ba0a71d880966dc442c993027b9660d`. |
| Standard runner retry in this environment | **ENVIRONMENT LIMIT** | The runner reached uv dependency bootstrap but could not resolve `hatchling` because this execution environment cannot connect to PyPI. This did not reach application test execution and is separate from the prior passing isolated runner evidence. |
| Approved README screenshot | **PASS** | [`assets/figures/inference-page.png`](../../assets/figures/inference-page.png) is a reviewed 1440×760 capture of the current Inference route with populated training/inference data, a visible suggestion, mixed outcomes, and no truncated meaningful content or excess blank bottom space. |

## Gate disposition

- **Passed:** `VAL-00`–`VAL-08`, `VAL-10`–`VAL-19`, `VAL-21`, and `VAL-22` for their recorded Windows/SQLite/CPU, PostgreSQL, CUDA, and supported desktop profiles; candidate lock, unit, lint, and build checks also passed.
- **Partial:** `STARTUP-01` and aggregate `validation.campaign` remain partial.
- **Blocked:** None.
- **Failed:** None.
- **Not tested:** None of the registered gates.
- **Deferred:** None of the pre-release validation gates.

## STARTUP-01 boundary

The official launcher remains an environment observation, not an application defect. Under the Codex execution identity, the launcher’s unconditional portable-runtime preparation attempted to rewrite `runtimes/python/python314._pth` and received Windows access denied; the canonical cache also contains protected residue. The already prepared repository runtime and the unchanged current build served the live application successfully for the reviewed screenshot. The user-confirmed PowerShell launcher path remains usable in their normal host context, but that does not make the protected Codex cold-launch path reproducible here. No permissions were broadened and no protected canonical cache or runtime file was changed.

## Release-operation status

Release operations completed after the validation decision: `develop` and `main` were fast-forwarded and pushed at `b7000413b071c263c4314b2e515aa570a5031018`; hosted candidate CI run `36235992990` passed all three jobs; annotated tag `v3.5.0` points to that commit; and the GitHub source release [FAIRS Roulette Player v3.5.0](https://github.com/CTCycle/FAIRS-Roulette-Player/releases/tag/v3.5.0) was published. These operations remain separate from the validation-gate disposition above.
