# TypeScript Guidelines (FAIRS Client)

Project-specific standards for `FAIRS/client` (React 19 + TypeScript + Vite).

## 1. Baseline

- Keep strict TypeScript settings (`tsconfig.app.json`).
- Keep `noUnusedLocals` and `noUnusedParameters` clean.
- Prefer explicit domain types over `any`.

## 2. Architecture Conventions

- Route composition belongs in `src/App.tsx`.
- Shared cross-page state belongs in `src/context/AppStateContext.tsx`.
- Page orchestration belongs in `src/pages/*`.
- Reusable UI and feature components belong in `src/components/*`.
- Keep API call helpers close to their feature unless shared extraction clearly improves maintainability.

## 3. Runtime and API Safety

- Treat backend payloads as untrusted; normalize before UI usage.
- Prefer typed parser/normalizer helpers for mixed numeric/string payload fields.
- Keep client fetch paths consistent with `/api/*` routing assumptions.

## 4. React Patterns

- Functional components + hooks only.
- Keep effects in `useEffect` with stable dependency lists.
- Prefer immutable state updates.
- Keep transient UI state local; use context only for truly shared state.

## 5. Tooling

Run from `FAIRS/client`:

```bash
npm run dev
npm run build
npm run lint
npm run preview
```

Linting uses ESLint flat config + `typescript-eslint` rules in `eslint.config.js`.

## 6. Testing Note

Automated frontend behavior is currently validated through Python Playwright E2E tests in `tests/e2e`.

If TypeScript unit/component tests are introduced (for example Vitest), update:

- `assets/docs/GUIDELINES_TESTS.md`
- `README.md` test commands
- CI/check commands
