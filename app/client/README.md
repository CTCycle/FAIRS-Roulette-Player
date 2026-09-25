# FAIRS frontend

The frontend is a React 19 + TypeScript + Vite single-page client for the local FAIRS backend. It is served through Vite during development and can be built into `app/client/dist` for the FastAPI SPA fallback.

## Structure

- `src/main.tsx` mounts the React tree.
- `src/App.tsx` composes `BrowserRouter`, `GuidanceProvider`, and the shared `MainLayout`.
- `src/pages/Training` owns the six-step training workflow, dataset/checkpoint previews, and live training monitor.
- `src/pages/Inference` composes the inference workspace and `components/inference/GameSession`.
- `src/components/Layout` contains the shared shell and navigation.
- `src/components/guidance` contains optional Help, walkthrough, and Tips & Tricks behavior.
- `src/hooks` own feature-local request/workflow state; pages own state that spans their child components.
- `src/types` contains frontend state and API response shapes.
- `src/utils` contains defensive payload parsing and dataset-upload helpers.

## Runtime boundary

All backend calls use the same-origin `/api/*` routes exposed by FastAPI. Training is started asynchronously and polled through `/api/training/status`; inference sessions are stateful within the backend process. The client does not access the database, checkpoint files, or ML modules directly.

The runtime FastAPI/Pydantic schemas are the canonical backend contract. `src/generated/api.ts` is generated from those schemas; OpenAPI is exported from the running backend when an external artifact is needed, and no checked-in `app/shared/openapi.json` is required. Client parsers remain defensive because runtime payloads can be malformed or evolve between versions.

## Development commands

Run these commands from the repository root with the managed Node runtime when available:

```powershell
& '.\runtimes\nodejs\npm.cmd' --prefix app/client run dev
& '.\runtimes\nodejs\npm.cmd' --prefix app/client run lint
& '.\runtimes\nodejs\npm.cmd' --prefix app/client run build
& '.\runtimes\nodejs\npm.cmd' --prefix app/client run preview
```

`npm run test:unit` runs the Vitest checks for client-owned payload conversion, API error parsing, and inference session storage. `npm run test:e2e` runs the Playwright desktop workflow and viewport checks against an existing Vite preview server with mocked API responses. Set `FRONTEND_E2E_BASE_URL` when the preview server is not at `http://127.0.0.1:4173`. The Windows standard runner and hosted CI supply the preview server. Playwright JUnit output, traces, and the retained 1100px/1099px screenshots are written under the repository's ignored `assets/QA/` directory.

On Windows, set `FRONTEND_E2E_BROWSER_CHANNEL=msedge` to run the same suite against the installed Microsoft Edge browser. Chromium remains the default and the hosted CI browser.

The Windows standard runner installs Node Playwright Chromium into its configured browser cache and executes both scripts. Backend lifecycle behavior remains covered by the Python Playwright suite.

Vite's dependency cache and TypeScript build-info files are written below `../../runtimes/cache` through `vite.config.ts` and the TypeScript project configurations. Do not add frontend cache paths under `node_modules` or the client source tree.

## Implementation guidance

- Keep route composition in `App.tsx`, page workflow state close to its page, and reusable request/status state in feature hooks.
- Keep API requests, parsing, loading, and error handling inside the consuming feature unless a small helper clearly removes duplication.
- Preserve existing design tokens, focus behavior, keyboard interactions, responsive layouts, and explicit loading/empty/error states.
- Avoid broad component rewrites; `GameSession` and the training preview/dashboard components are intentionally identified as future extraction candidates in the architecture review.

See [`../../assets/docs/architecture/system_overview.md`](../../assets/docs/architecture/system_overview.md) and [`../../assets/docs/coding/typescript.md`](../../assets/docs/coding/typescript.md) for the repository-wide architecture and coding rules.
