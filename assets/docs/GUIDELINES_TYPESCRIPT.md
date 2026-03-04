# TypeScript Guidelines (FAIRS Client)

Project-specific standards for `FAIRS/client` (React 19 + TypeScript + Vite).

## 1. Baseline

- Use strict TypeScript (`tsconfig.app.json` is strict).
- Keep `noUnusedLocals` and `noUnusedParameters` clean.
- Prefer explicit domain types from `src/types` and context interfaces over inline `any`.

## 2. Architecture conventions

- Route composition stays in `src/App.tsx`.
- Shared cross-page state goes through `src/context/AppStateContext.tsx`.
- Page-level orchestration lives in `src/pages/*`.
- Reusable UI logic belongs in `src/components/*`.
- Keep API calls close to the feature they support unless extraction clearly improves reuse.

## 3. API and runtime safety

- Treat API payloads as untrusted: normalize/validate response fields before use.
- Prefer helper normalizers (`maybeNumber`, parser helpers) for mixed backend payloads.
- Keep `/api/*` fetch paths consistent with Vite/Nginx proxy assumptions.

## 4. Tooling

- Build: `npm run build`
- Lint: `npm run lint`
- Dev server: `npm run dev`
- Preview: `npm run preview`

Use ESLint (flat config) and `typescript-eslint` rules already configured in `eslint.config.js`.

## 5. React patterns

- Use functional components and hooks only.
- Keep side effects in `useEffect` with stable dependencies.
- Prefer immutable updates for complex state transitions.
- Avoid over-centralizing ephemeral UI state; keep local state local.

## 6. Testing note

Current automated frontend behavior coverage is provided by Python Playwright E2E tests in `tests/e2e`.
If introducing TS unit/component tests, align with Vite-compatible tooling (for example Vitest) and document the command changes.
