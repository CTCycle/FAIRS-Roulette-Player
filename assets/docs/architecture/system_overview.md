## System Overview

Last updated: 2026-06-02

## Summary

FAIRS is a Windows-first roulette research application with three main runtime surfaces:

- FastAPI backend in `app/server`
- React + TypeScript frontend in `app/client/src`
- Optional Tauri desktop shell in `app/src-tauri`

The backend is the system of record for API behavior, training orchestration, inference sessions, and persistence.

## Source Tree

The structure below is source-focused and excludes dependency, cache, and generated folders such as `node_modules`, `dist`, `target`, `__pycache__`, and `.pytest_cache`.

```text
.
├─ app/
│  ├─ client/
│  │  ├─ package.json
│  │  ├─ vite.config.ts
│  │  ├─ src/
│  │  │  ├─ App.tsx
│  │  │  ├─ main.tsx
│  │  │  ├─ components/
│  │  │  ├─ context/
│  │  │  ├─ hooks/
│  │  │  ├─ pages/
│  │  │  ├─ styles/
│  │  │  ├─ types/
│  │  │  └─ utils/
│  │  └─ src-tauri/
│  │     ├─ Cargo.toml
│  │     ├─ tauri.conf.json
│  │     ├─ capabilities/
│  │     ├─ icons/
│  │     └─ src/main.rs
│  ├─ resources/
│  │  ├─ checkpoints/
│  │  ├─ logs/
│  │  └─ database.db
│  ├─ scripts/
│  │  └─ initialize_database.py
│  ├─ server/
│  │  ├─ app.py
│  │  ├─ pyproject.toml
│  │  ├─ api/
│  │  ├─ common/
│  │  ├─ configurations/
│  │  ├─ domain/
│  │  ├─ learning/
│  │  ├─ repositories/
│  │  └─ services/
│  ├─ shared/
│  │  └─ openapi.json
│  └─ tests/
│     ├─ conftest.py
│     ├─ run_tests.bat
│     ├─ e2e/
│     └─ unit/
├─ assets/
│  └─ docs/
├─ release/
│  └─ tauri/
│     ├─ build_with_tauri.bat
│     └─ scripts/
├─ runtimes/
├─ settings/
│  └─ configurations.json
├─ start_on_windows.ps1
└─ start_on_windows.ps1
```

## Entry Points

- Backend app entry:
  - `app/server/app.py`
- Local launcher:
  - `start_on_windows.ps1`
- Maintenance launcher:
  - `start_on_windows.ps1`
- Frontend entry:
  - `app/client/src/main.tsx`
- Frontend route composition:
  - `app/client/src/App.tsx`
- Desktop shell entry:
  - `app/src-tauri/src/main.rs`
- Desktop packaging helper:
  - `release/tauri/build_with_tauri.bat`

## Frontend Structure

- App shell uses `BrowserRouter` with `MainLayout` as the shared route frame.
- The root route redirects to `/training`.
- Primary pages are:
  - `/training`
  - `/inference`
- Shared application state lives in `src/context`.
- Feature logic is split between `src/hooks`, `src/pages`, and `src/components`.
- Styling is token-driven through `src/styles/global.css` plus feature CSS files and CSS modules.

## Related Files

- Read `backend_api.md` for the mounted HTTP surface.
- Read `execution_and_data_flow.md` for service layering and orchestration chains.
- Read `persistence.md` for stored data, checkpoints, and logs.
