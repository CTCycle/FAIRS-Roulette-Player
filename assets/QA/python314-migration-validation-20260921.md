# Python 3.14 migration validation

Date: 2026-09-21

## Runtime and dependency evidence

- The supported Development installer completed successfully.
- Portable runtime: Python `3.14.7`.
- Backend environment: `app/server/.venv` recreated for Python 3.14.
- Locked ML runtime: `torch==2.10.0+cu130`.
- `app/server/uv.lock` now declares `requires-python = "==3.14.*"`.
- Frontend production build and Playwright Chromium installation completed.
- Direct smoke: `torch.compile(lambda value: value + 1, backend="eager")` executed under Python 3.14 and returned `5`.

## Automated validation

The repository-standard `app/tests/run_tests.bat` completed with the elevated Windows token required by the existing ACL on the canonical pytest cache:

```text
Live server phase   : PASS
Python tests        : PASS
Frontend bootstrap  : PASS
Frontend unit tests : SKIPPED
Frontend E2E tests  : SKIPPED
199 passed, 9 skipped, 1 warning in 103.94s
```

The nine pytest skips were five PostgreSQL cases without `TEST_POSTGRES_URL` and four checkpoint-backed live-inference cases without a usable fixture. The one warning is the existing AnyIO deprecation warning. The focused capability/settings slice also passed separately: `9 passed, 1 warning`.

The portable Node runtime's `npm run lint` passed. The installer production build passed.

## Browser and waiting-state smoke

The supported launcher option 1 served the frontend on `http://127.0.0.1:8051/`; the in-app browser reached `/training`, displayed `Connected`, and rendered the training workspace. With the backend stopped while the frontend remained served, the root waiting screen displayed `Preparing the table…`, `Starting the FAIRS backend.`, and `Waiting for a healthy response` with `aria-busy="true"`.

At two samples 650 ms apart, the startup rotor and orbit reported `animationPlayState: running` and different transforms. The waiting animation therefore advances in the current Python 3.14 build.

The temporary browser tab was closed and ports `8890` and `8051` were verified to have no listeners after validation.
