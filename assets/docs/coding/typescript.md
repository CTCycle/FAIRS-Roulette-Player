## TypeScript

Last updated: 2026-07-20

## Baseline

- Keep strict TypeScript settings enabled through the project `tsconfig` files.
- Avoid `any`.
- Define domain-level types in `app/client/src/types` or the closest feature module.
- Keep API payload parsing defensive through the existing parser and normalizer utilities.

## Frontend Architecture Rules

- Route composition and top-level wiring belong in `app/client/src/App.tsx`.
- Shared app state belongs in `app/client/src/context` and related hooks.
- Page orchestration belongs in `app/client/src/pages`.
- Reusable view units belong in `app/client/src/components`.
- Keep API requests scoped to the consuming feature unless extraction clearly reduces duplication.

## React Patterns

- Use functional components and hooks.
- Keep state updates immutable.
- Keep effect dependencies explicit and stable.
- Keep local UI state close to the component that owns it.
- Use context only for state that must cross page or feature boundaries.

## UI Implementation Rules

- Reuse the existing design tokens from `app/client/src/styles/global.css`.
- Preserve keyboard-safe and focus-safe interactions.
- Keep error, loading, and empty-state behavior consistent across pages.
- Prefer existing patterns before introducing parallel styling or state conventions.
- Normalize optional numeric training metrics at the UI boundary so missing or invalid telemetry does not break charts.

## Tooling

Use the npm scripts from `app/client/package.json`:

- `npm run dev`
- `npm run build`
- `npm run lint`
- `npm run preview`

## Related Files

- Read `../ui/design_tokens.md` and `../ui/components_and_patterns.md` for implementation-facing UI standards.
- Read `testing_and_quality.md` for validation expectations before shipping frontend changes.
