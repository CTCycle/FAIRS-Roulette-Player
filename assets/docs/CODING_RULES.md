# CODING_RULES

Last updated: 2026-04-24

This file is the consolidated coding standard for this repository.

## Python Rules

### Runtime and tooling baseline

- Target Python version: `>=3.14` (from `pyproject.toml`).
- Use virtual environment: `runtimes/.venv` when present; otherwise use the repository default environment policy.
- Keep dependencies managed with `uv` and keep lock state aligned with `runtimes/uv.lock`.
- Prefer running Python tools via `uv run ...` from repository root.

### Typing

- Type annotations are required for public APIs and non-trivial internal logic.
- Use built-in generics (`list[str]`, `dict[str, Any]`, etc.).
- Use `|` for unions.
- Use `collections.abc` for abstract interfaces (`Callable`, iterables, mappings) where appropriate.
- Treat typing as a quality gate, not optional documentation.

### Validation and APIs

- Use Pydantic/domain models for request and response validation.
- Avoid ad-hoc manual validation when domain models can enforce constraints.
- Return explicit HTTP status codes and consistent response models.
- Map errors safely and deterministically (no raw internal traces in API payloads).
- Preserve traceability for jobs and requests using IDs (`job_id`, `session_id`, etc.).

### Async and concurrency

- Use `async` only with non-blocking operations.
- Do not run CPU-heavy model workloads in async request handlers.
- Use the existing job orchestration pattern (`JobManager` + worker process) for long-running training tasks.
- Long-running operations should expose start, poll/status, and cancel/stop APIs.

### Code structure

- Keep functions cohesive and small.
- Keep side effects explicit.
- Prefer simple, composable logic over deeply coupled abstractions.
- Add comments only when needed for non-obvious constraints or safety rationale.
- Follow existing module boundaries (`api`, `services`, `domain`, `repositories`, `learning`, `configurations`).
- Avoid repository-wide stylistic churn unrelated to the task.
- Keep modules approximately under 1000 LOC where practical.
- Keep imports at file top.
- Avoid nested functions unless there is a clear locality benefit.
- Use classes to group related stateful logic when that improves cohesion.

### Persistence and configuration

- Route data access through repository serializers/queries instead of direct DB logic in API modules.
- Keep schema, serializer, and API contracts synchronized in the same change.
- Runtime process flags come from `.env`; technical backend settings come from `FAIRS/settings/configurations.json`.

### Quality tooling

- Lint/format with Ruff (or project-equivalent configured tooling).
- Type checking baseline: Pylance-compatible type discipline.
- Testing baseline: `pytest` with emphasis on `tests/unit` and relevant `tests/e2e`.

## TypeScript Rules

Derived from the current React + TypeScript frontend implementation.

### Baseline

- Keep strict TypeScript configuration (`tsconfig.app.json`) enabled.
- Avoid `any`; define domain-level interfaces/types in `src/types` or feature modules.
- Keep API payload parsing defensive (`apiParsers.ts`, feature normalizers).

### Architecture

- Routes and top-level app wiring belong in `src/App.tsx`.
- Shared app state belongs in `src/context` and hooks (`src/hooks`).
- Page orchestration belongs in `src/pages`.
- Reusable UI units belong in `src/components`.
- Keep API requests scoped to the feature consuming them unless common extraction clearly reduces duplication.

### React patterns

- Use functional components and hooks.
- Keep state updates immutable.
- Keep effect dependencies explicit and stable.
- Keep transient/local UI state near the component; use context only for shared cross-page state.

### UI and accessibility

- Reuse existing design tokens in `src/styles/global.css`.
- Provide keyboard/focus-safe interactions for controls.
- Keep consistent error/loading/empty-state behavior across pages.

### Tooling

- Use existing npm scripts from `FAIRS/client/package.json`:
  - `npm run dev`
  - `npm run build`
  - `npm run lint`
  - `npm run preview`

## Rust and Batch/PowerShell Rules (Project-Specific)

- Keep Tauri startup/build logic aligned with existing launcher expectations (`runtimes` layout, `.env` parsing, uv sync flow).
- Preserve Windows-first behavior in `.bat` and PowerShell automation scripts.
- Do not introduce conflicting runtime bootstrap paths outside established scripts unless explicitly required.
