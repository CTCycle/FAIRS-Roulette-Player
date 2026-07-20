## System Overview

Last updated: 2026-07-20

## Summary

FAIRS is a Windows-first roulette research application with two main runtime surfaces:

- FastAPI backend in `app/server`
- React + TypeScript frontend in `app/client/src`
- Current application version: `2.5.0`

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
├─ runtimes/
├─ settings/
│  └─ configurations.json
└─ start_on_windows.ps1
```

## Entry Points

- Backend app entry:
  - `app/server/app.py`
- Local launcher:
  - `start_on_windows.ps1`
- Frontend entry:
  - `app/client/src/main.tsx`
- Frontend route composition:
  - `app/client/src/App.tsx`

## Frontend Structure

- App shell uses `BrowserRouter` with `MainLayout` as the shared route frame.
- The root route redirects to `/training`.
- Primary pages are:
  - `/training`
  - `/inference`
- Shared application state lives in `src/context`.
- Feature logic is split between `src/hooks`, `src/pages`, and `src/components`.
- Styling is token-driven through `src/styles/global.css` plus feature CSS files and CSS modules.
- Training includes dataset/checkpoint previews, a multi-step configuration wizard, and live metric/history charts.

## Related Files

- Read `backend_api.md` for the mounted HTTP surface.
- Read `execution_and_data_flow.md` for service layering and orchestration chains.
- Read `persistence.md` for stored data, checkpoints, and logs.
