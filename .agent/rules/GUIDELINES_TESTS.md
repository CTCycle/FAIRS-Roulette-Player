# HOW TO TEST (FAIRS)

This document describes the current FAIRS testing strategy and commands.

## 1. Test stack

- Test runner: `pytest`
- Browser/API E2E layer: `pytest-playwright`
- Language: Python

FAIRS currently relies on Python-based unit + E2E tests. There is no separate TypeScript unit-test suite in this repository.

## 2. Test suite structure

```text
tests/
├── conftest.py
├── run_tests.bat
├── test_config.json
├── unit/
│   ├── test_data_serializer.py
│   ├── test_database_mode_env_override.py
│   ├── test_fallback.py
│   ├── test_hold.py
│   └── test_sizer.py
└── e2e/
    ├── test_app_flow.py
    ├── test_data_removal_api.py
    ├── test_database_api.py
    ├── test_inference_api.py
    ├── test_training_api.py
    ├── test_upload_api.py
    └── test_websocket.py
```

## 3. Quick start (recommended)

Run from repository root:

```cmd
tests\run_tests.bat
```

What the script does:

1. Resolves host/port/runtime values from `FAIRS/settings/.env`.
2. Verifies `.venv` and required tools.
3. Starts backend/frontend if not already running.
4. Runs `pytest tests -v --tb=short`.
5. Stops only the servers started by the script.

## 4. Prerequisites

- Run `FAIRS\start_on_windows.bat` at least once.
- If E2E dependencies are needed, set `OPTIONAL_DEPENDENCIES=true` in `FAIRS/settings/.env` and rerun launcher to install extras.
- Ensure no conflicting processes are bound to your selected UI/API ports.

## 5. Manual test execution

From repository root:

```cmd
uv run pytest -q tests\unit
uv run pytest -q tests\e2e
```

Useful filters:

```cmd
uv run pytest -q tests\e2e\test_training_api.py -k cancel
uv run pytest -q tests\e2e\test_app_flow.py --headed
```

## 6. Current API coverage

### Data ingestion
- `POST /data/upload`

### Dataset browsing/removal
- `GET /database/roulette-series/datasets`
- `GET /database/roulette-series/datasets/summary`
- `DELETE /database/roulette-series/datasets/{dataset_id}`

### Training lifecycle
- `POST /training/start`
- `POST /training/resume`
- `GET /training/status`
- `POST /training/stop`
- `GET /training/checkpoints`
- `GET /training/checkpoints/{checkpoint}/metadata`
- `DELETE /training/checkpoints/{checkpoint}`
- `GET /training/jobs/{job_id}`
- `DELETE /training/jobs/{job_id}`

### Inference lifecycle
- `POST /inference/sessions/start`
- `POST /inference/sessions/{session_id}/next`
- `POST /inference/sessions/{session_id}/step`
- `POST /inference/sessions/{session_id}/bet`
- `POST /inference/sessions/{session_id}/shutdown`
- `POST /inference/sessions/{session_id}/rows/clear`
- `POST /inference/context/clear`

## 7. Writing new tests

- Unit tests: place under `tests/unit`.
- E2E tests: place under `tests/e2e`.
- Naming: `test_*.py`.
- Keep Arrange-Act-Assert flow explicit.
- Use `api_context` fixture for API calls and `page` fixture for UI checks.
- Prefer deterministic inputs and short-running configs (especially training tests).

## 8. Common troubleshooting

- `422` responses on POST endpoints are often request-shape or missing field issues.
- If Playwright tests fail before running, verify optional dependencies and browsers are installed in `.venv`.
- If E2E readiness fails, check `APP_TEST_BACKEND_URL` / `APP_TEST_FRONTEND_URL` derivation from `.env` values.
