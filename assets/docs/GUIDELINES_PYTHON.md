# Engineering and Python Standards

Last updated: 2026-04-09

Project-specific Python standards for FAIRS backend, scripts, and tests.

## 1. Runtime Baseline

- Target runtime: Python `3.14+` (matches `pyproject.toml` and launcher-managed runtime).
- Package/dependency tooling: `uv`.
- Virtual environment for local execution/tests: `runtimes/.venv`.

Recommended invocation patterns from repo root:

```powershell
.\runtimes\.venv\Scripts\python.exe -m pytest tests\unit
uv run python -m uvicorn FAIRS.server.app:app --host 127.0.0.1 --port 5000
```

## 2. Typing and Validation

- Type hints are required for public APIs and non-trivial internal logic.
- Use built-in generics (`list`, `dict`, `tuple`) and `|` unions.
- Prefer `collections.abc` for `Callable` and similar abstract collection types.
- Use Pydantic/domain models for request/response contracts in API boundaries.

## 3. Imports and Module Layout

- Keep imports at module top level.
- Avoid conditional imports unless absolutely required for platform/runtime guards.
- Keep modules cohesive by feature/domain (`api`, `services`, `learning`, `repositories`, `configurations`).
- Follow existing package structure before introducing new top-level folders.

## 4. Style and Readability

- Follow PEP 8 and existing repository style.
- Preserve existing section separator convention in backend modules where already used.
- Use clear names and small single-purpose functions/classes.
- Add comments only when they explain non-obvious behavior or constraints.

## 5. FastAPI Conventions

- Register endpoint modules from `FAIRS/server/api` through `FAIRS/server/app.py`.
- Keep endpoint modules focused on HTTP mapping and validation.
- Move heavy business logic to services/learning/repositories layers.
- Do not run CPU-heavy training work directly in request thread; use the job manager + worker pattern.

## 6. Configuration and Environment

- Runtime/process configuration source of truth: `FAIRS/settings/.env`.
- Backend technical defaults source of truth: `FAIRS/settings/configurations.json`.
- Use `FAIRS.server.configurations.settings` (`AppSettings`/`get_app_settings`) and `FAIRS.server.configurations.server` (`get_server_settings`/`server_settings`) instead of ad-hoc `os.getenv`.
- Environment bootstrap must happen through `FAIRS.server.configurations.bootstrap.ensure_environment_loaded`.
- Settings source precedence must remain: init kwargs -> environment variables -> JSON configuration -> file secrets.
- Technical env overrides must use explicit keys only:
  - `DATABASE_EMBEDDED_DATABASE`, `DATABASE_ENGINE`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_DATABASE_NAME`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_SSL`, `DATABASE_SSL_CA`, `DATABASE_CONNECT_TIMEOUT`, `DATABASE_INSERT_BATCH_SIZE`
  - `JOBS_POLLING_INTERVAL`
  - `DEVICE_JIT_COMPILE`, `DEVICE_JIT_BACKEND`, `DEVICE_USE_MIXED_PRECISION`
- Keep `.env` keys coherent with `PACKAGING_AND_RUNTIME_MODES.md` and README.

## 7. Persistence and Data Access

- Use repository/serializer abstractions under `FAIRS/server/repositories`.
- Avoid embedding SQL/data-frame mutation logic directly in API modules.
- Keep persistence models and serializers synchronized when schema changes.

## 8. Testing Expectations

- Test framework: `pytest`.
- Unit tests under `tests/unit`, E2E/API flows under `tests/e2e`.
- For behavior changes, add/adjust tests in the same change when practical.
- Use deterministic inputs and stable assertions; avoid flaky timing dependencies.

## 9. Quality Gates

Before shipping Python changes, run the smallest relevant checks first, then full scope as needed:

```powershell
uv run pytest -q tests\unit
uv run pytest -q tests\e2e
```

If tooling/config changes were made, also run lint/type checks used by project CI.
