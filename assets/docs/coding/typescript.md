## TypeScript

Last updated: 2026-09-01

## Baseline

- Keep strict TypeScript settings enabled through the project `tsconfig` files.
- The current frontend baseline is React `19.2`, React Router `7.10`, TypeScript `5.9`, and Vite `7.2`.
- Avoid `any`.
- Define frontend state and API contract types in `app/client/src/types` or the closest feature module. These are client contracts, not shared Python domain entities.
- Keep API payload parsing defensive through the existing parser and normalizer utilities.

## Frontend Architecture Rules

- Route composition and top-level wiring belong in `app/client/src/App.tsx`.
- Keep workflow state local to the owning page or feature hook. Use context only for true cross-cutting UI concerns such as guidance.
- Page orchestration belongs in `app/client/src/pages`.
- Reusable view units belong in `app/client/src/components`.
- Keep API requests scoped to the consuming feature unless extraction clearly reduces duplication.
- Keep fetch, response parsing, loading, and error state together in a feature hook/helper when extracting them reduces duplication; do not create a generic client layer for one endpoint.
- Treat `app/shared/openapi.json` as the backend contract source for route and payload review, while keeping defensive parsing at the browser boundary.

## React Patterns

- Use functional components and hooks.
- Keep state updates immutable.
- Keep effect dependencies explicit and stable.
- Every effect must mirror setup with cleanup. Abort requests, clear timers, unsubscribe observers, and ignore stale responses after dependency changes or unmount. The app intentionally keeps React Strict Mode enabled.
- Pass `AbortSignal` through API helpers. Read-only readiness/status requests may use capped reconnect backoff; mutating operations are not retried automatically.
- Persist only an advisory inference-session descriptor in `localStorage`. Recover through the backend snapshot endpoint on mount; remove the descriptor only after explicit Stop or confirmed expiration.
- Serialize inference mutations. Transactional recomputation creates and replays a replacement first, then switches UI ownership only after success; failed replay retains the old session.
- Keep local UI state close to the component that owns it.
- Do not create a global application-state store for training or inference workflows; pass typed snapshots through the owning page boundary.

## UI Implementation Rules

- Reuse the existing design tokens from `app/client/src/styles/global.css`.
- Preserve keyboard-safe and focus-safe interactions.
- Keep error, loading, and empty-state behavior consistent across pages.
- Prefer existing patterns before introducing parallel styling or state conventions.
- Normalize optional numeric training metrics at the UI boundary so missing or invalid telemetry does not break charts.
- Keep training data adapters aligned with the backend's canonical dataset and serializer fields; do not reintroduce the pre-encoding synthetic `extraction` shape.

## Tooling

Use the npm scripts from `app/client/package.json`:

- `npm run dev`
- `npm run build`
- `npm run lint`
- `npm run preview`

The frontend package does not currently define `test:unit` or `test:e2e` scripts; the standard Windows test runner detects and skips those phases when absent.

## Related Files

- Read `../ui/design_tokens.md` and `../ui/components_and_patterns.md` for implementation-facing UI standards.
- Read `testing_and_quality.md` for validation expectations before shipping frontend changes.
