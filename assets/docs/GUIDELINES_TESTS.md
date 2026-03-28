# How To Test (FAIRS)

Current FAIRS test strategy and execution commands.

## 1. Test Stack

- Runner: `pytest`
- Browser E2E: `pytest-playwright`
- Language: Python

There is currently no dedicated TypeScript unit/component test suite in this repository.

## 2. Test Suite Structure

```text
tests/
├── conftest.py
├── run_tests.bat
├── test_config.json
├── scripts/
│   └── ...
├── unit/
│   ├── test_data_serializer.py
│   ├── test_database_mode_env_override.py
│   ├── test_fallback.py
│   ├── test_hold.py
│   ├── test_security_hardening.py
│   ├── test_sizer.py
│   └── test_sqlite_repository_orm.py
└── e2e/
    ├── test_app_flow.py
    ├── test_data_removal_api.py
    ├── test_database_api.py
    ├── test_inference_api.py
    ├── test_training_api.py
    ├── test_upload_api.py
    └── test_websocket.py
```

## 3. Recommended Command

From repository root:

```cmd
tests\run_tests.bat
```

The script:

1. Loads host/port/runtime values from `FAIRS/settings/.env`.
2. Requires `runtimes/.venv` (created by `FAIRS/start_on_windows.bat`).
3. Starts backend/frontend only when not already running.
4. Runs `pytest tests -v --tb=short`.
5. Stops only servers it started.

## 4. Prerequisites

- Run `FAIRS\start_on_windows.bat` at least once.
- If Playwright/test extras are required, set `OPTIONAL_DEPENDENCIES=true` in `.env` and rerun launcher.
- Ensure selected UI/API ports are not already occupied by unrelated processes.

## 5. Manual Test Commands

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

## 6. API Coverage (Current)

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

## 7. Writing New Tests

- Place unit tests in `tests/unit`.
- Place E2E/integration UI/API flows in `tests/e2e`.
- Use `test_*.py` naming.
- Keep Arrange-Act-Assert explicit.
- Prefer deterministic data and short runtime configs.
- Reuse fixtures from `tests/conftest.py` where possible.

## 8. Common Troubleshooting

- `422` responses usually indicate payload/query mismatch.
- Playwright import/browser errors usually mean optional dependencies were not installed into `runtimes/.venv`.
- Readiness failures often come from `.env` host/port mismatch versus expected test URLs.
