# FAIRS frontend

The frontend is a React 19 + TypeScript + Vite single-page client for the local FAIRS backend. It is served through Vite during development and can be built into `app/client/dist` for the FastAPI SPA fallback.

## Structure

- `src/main.tsx` mounts the React tree.
- `src/App.tsx` composes `BrowserRouter`, `AppStateProvider`, `GuidanceProvider`, and the shared `MainLayout`.
- `src/pages/Training` owns the six-step training workflow, dataset/checkpoint previews, and live training monitor.
- `src/pages/Inference` composes the inference workspace and `components/inference/GameSession`.
- `src/components/Layout` contains the shared shell and navigation.
- `src/components/guidance` contains optional Help, walkthrough, and Tips & Tricks behavior.
- `src/context` and `src/hooks` own shared state and feature-local request/workflow state.
- `src/types` contains frontend state and API response shapes.
- `src/utils` contains defensive payload parsing and dataset-upload helpers.

## Runtime boundary

All backend calls use the same-origin `/api/*` routes exposed by FastAPI. Training is started asynchronously and polled through `/api/training/status`; inference sessions are stateful within the backend process. The client does not access the database, checkpoint files, or ML modules directly.

The checked-in `app/shared/openapi.json` documents the backend route and payload contract. Client parsers remain defensive because runtime payloads can be malformed or evolve between versions.

## Development commands

Run these commands from the repository root with the managed Node runtime when available:

```powershell
& '.\runtimes\nodejs\npm.cmd' --prefix app/client run dev
& '.\runtimes\nodejs\npm.cmd' --prefix app/client run lint
& '.\runtimes\nodejs\npm.cmd' --prefix app/client run build
& '.\runtimes\nodejs\npm.cmd' --prefix app/client run preview
```

The package currently defines lint, build, dev, and preview scripts but no standalone frontend unit or E2E script. The repository test runner detects that state and skips absent frontend test phases.

## Implementation guidance

- Keep route composition in `App.tsx`, cross-page state in context, and feature state close to its page or hook.
- Keep API requests, parsing, loading, and error handling inside the consuming feature unless a small helper clearly removes duplication.
- Preserve existing design tokens, focus behavior, keyboard interactions, responsive layouts, and explicit loading/empty/error states.
- Avoid broad component rewrites; `GameSession` and the training preview/dashboard components are intentionally identified as future extraction candidates in the architecture review.

See [`../../assets/docs/architecture/system_overview.md`](../../assets/docs/architecture/system_overview.md) and [`../../assets/docs/coding/typescript.md`](../../assets/docs/coding/typescript.md) for the repository-wide architecture and coding rules.
