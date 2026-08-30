## Python

Last updated: 2026-08-30

## Runtime Baseline

- Target Python version:
  - `>=3.14`
- The launcher currently stages portable CPython `3.14.2`.
- Preferred environment:
  - `app/server/.venv` when present
  - otherwise follow the repository environment policy
- Keep dependencies managed with `uv`.
- Prefer running Python tooling from repository root with `uv run ...`.
- Development-only test and tooling dependencies are declared under the `test` optional extra and installed through the launcher's `Development` mode or `uv sync --extra test`.

## Typing Rules

- Type annotations are required for public APIs and non-trivial internal logic.
- Use built-in generics such as `list[str]` and `dict[str, Any]`.
- Use `|` for unions.
- Prefer `collections.abc` types for abstract interfaces where appropriate.
- Treat typing as a quality gate, not optional decoration.

## Validation And API Rules

- Use `server.contracts` Pydantic models for request/response validation and runtime settings. These are boundary contracts, not ORM entities or a general-purpose domain layer.
- Avoid ad-hoc manual validation when a model can encode the constraint.
- Return explicit HTTP status codes and stable response shapes.
- Do not expose raw internal traces in API payloads.
- Preserve traceability with identifiers such as `job_id` and `session_id`.

## Async And Concurrency Rules

- Use `async` only for genuinely non-blocking operations.
- Do not run CPU-heavy model workloads in async request handlers.
- Follow the existing long-running task pattern:
  - start endpoint
  - status endpoint
  - stop or cancel endpoint
- Reuse `TrainingRunManager` plus the worker-process model for training workloads. `TrainingRunManager` is the single in-process training-run state owner.

## Structure Rules

- Keep functions cohesive and small.
- Keep side effects explicit.
- Prefer simple, composable logic over deep abstraction stacks.
- Add comments only for non-obvious constraints or safety rationale.
- Respect the existing backend module boundaries:
  - `api`
  - `services`
  - `contracts`
  - `repositories`
  - `learning`
  - `configurations`
- Keep dependency direction explicit:
  - contracts do not depend on API, services, repositories, configuration loaders, or learning;
  - API handlers do not access repositories or learning directly;
  - repositories do not depend on API or services;
  - learning code does not depend on API, services, or repositories.
- Put shared roulette transformations in the named `common.roulette` module rather than duplicating feature derivation in repositories and learning code.
- Avoid unrelated stylistic churn.
- Keep imports at file top.
- Avoid nested functions unless locality clearly improves the code.
- Use classes where stateful cohesion benefits readability.

## Persistence And Settings Rules

- Route data access through `DatasetRepository`, `InferenceRepository`, and `CheckpointRepository`; do not construct databases inside API handlers.
- Keep schema, serializer, and API contracts synchronized.
- Runtime flags come from environment variables.
- Structured non-env settings live in `settings/configurations.json`.
- Database connection and selection settings live in `settings/.env`; do not add a `database` block to the JSON settings file.
- Synthetic training data must preserve the canonical roulette `outcome` input through encoding and expose the training environment's `extraction` column at the serializer boundary.

## Related Files

- Read `testing_and_quality.md` for tests and linting expectations.
- Read `../architecture/execution_and_data_flow.md` for how these rules map onto the backend layers.
