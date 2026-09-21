# FAIRS startup launch smoke

Result: `PASS`

Date: 2026-09-20  
Checkout: `develop` at `c2d8039`  
Scope: Windows launcher menu option 1, automatic browser handoff, rendered readiness, startup E2E coverage, and cleanup.

## Direct launcher evidence

- Ports `8051` and `8890` were clear before launch.
- `.\start_on_windows.ps1` menu option 1 completed with `[OK] FAIRS frontend is ready.`
- The launcher reported `http://127.0.0.1:8890` for the backend and `http://127.0.0.1:8051` for the frontend.
- Chrome automatically opened a tab titled `FAIRS Roulette Player` at `http://127.0.0.1:8051/training`.
- The rendered page showed the FAIRS training workspace, `Training Monitor`, and `Connected`.
- The only captured browser error was the local Chrome wrapper message `Could not establish connection. Receiving end does not exist.`; it was emitted at the wrapper page URL and was not an application request or FAIRS console failure.

## Automated evidence

- `TestStartupFlow`: `6 passed` with no warnings using the repository-local disposable test cache.
- Full repository-local pytest run: `201 passed, 10 skipped, 1 warning in 66.31s`.
- Frontend lint: `PASS`.
- Frontend production build: `PASS`.

## Boundary and cleanup

- The exact `app/tests/run_tests.bat` retry was blocked before collection because the existing `runtimes/cache/uv` cache returned Windows access denied. No ACL broadening or deletion of the protected canonical cache was performed.
- The disposable `app/tests/.pytest_cache` and `app/tests/.uv-cache` directories used for the equivalent repository-local run were removed. The generated `app/tests/.pytest-tmp/full-suite` directory remains because its inherited ACL denied deletion; it is outside application data and did not affect the final process or port check.
- After the smoke, no FAIRS process remained and ports `8051` and `8890` had no listeners. Unrelated XREPORT processes were preserved.
