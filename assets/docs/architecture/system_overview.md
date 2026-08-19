## System Overview

Last updated: 2026-08-19

## Summary

FAIRS is a Windows-first roulette research application for local web-mode roulette training and inference experiments. It has two main runtime surfaces:

- FastAPI backend in `app/server`
- React 19 + TypeScript frontend in `app/client/src`
- Current application version: `2.9.0`

The backend is the system of record for API behavior, training orchestration, inference sessions, persistence, and startup readiness. The repository does not include a desktop installer, container deployment, or packaged executable path.

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
│  │  ├─ export_openapi.py
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
│  ├─ docs/
│  └─ figures/
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
- The shared header includes the FAIRS logo, workspace subtitle, and icon-backed Training/Inference navigation.
- Shared application state lives in `src/context`.
- Feature logic is split between `src/hooks`, `src/pages`, and `src/components`.
- Styling is token-driven through `src/styles/global.css` plus feature CSS files and CSS modules.
- Training includes dataset/checkpoint previews, a clickable six-step configuration wizard, and a live monitor with metric cards, progress, and history charts.
- Inference uses a setup/statistics/suggestion panel beside a session-history table with Play, Stop, Clear, and row-edit controls.

## Related Files

- Read `backend_api.md` for the mounted HTTP surface.
- Read `execution_and_data_flow.md` for service layering and orchestration chains.
- Read `persistence.md` for stored data, checkpoints, and logs.
