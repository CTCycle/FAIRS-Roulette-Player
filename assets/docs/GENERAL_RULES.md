## WEB SEARCH
Use web search only when it materially improves accuracy (for example, external tool behavior or version changes). Prefer repository source of truth for project-specific facts.

## REQUIRED DOCUMENTATION REVIEW
Before any task, review the relevant files in `assets/docs`:

- `GENERAL_RULES.md` (mandatory for every task)
- `ARCHITECTURE.md` (system structure, modules, API surface)
- `PACKAGING_AND_RUNTIME_MODES.md` (launcher, runtime profiles, desktop packaging)
- `BACKGROUND_JOBS.md` (job lifecycle and cancellation model)
- `GUIDELINES_PYTHON.md` (when editing Python)
- `GUIDELINES_TYPESCRIPT.md` (when editing TypeScript/React)
- `GUIDELINES_TESTS.md` (when adding/updating tests)
- `README_WRITING.md` (when creating/updating README files)

Read only the minimum subset needed for the task after this file.

## SKILLS REFERENCE
When reusable workflows or specialized capabilities are needed, use the relevant skills from the skills repository.

## DOCUMENTATION UPDATES
If changes materially affect behavior, architecture, runtime, or usage:

1. Update the relevant files in `assets/docs`.
2. Keep docs coherent with each other and with repository source files.
3. Call out documentation changes in the task summary.

## CROSS-LANGUAGE PRINCIPLES

### Code quality
- Prefer clear naming, cohesive modules, and low coupling.
- Optimize for readability, maintainability, and testability.

### Testing and automation
- Keep CI checks green: formatting, linting, type checks, and tests.
- Add or update tests for behavior changes when practical.

### Security
- Validate inputs, protect secrets, and minimize attack surface.
- Avoid introducing implicit trust boundaries.

## EXECUTION RULES
- Use PowerShell by default for terminal commands in this repository.
- Use `cmd /c` only for `.bat` scripts or CMD-specific syntax.
- For Python execution, use `runtimes/.venv` (directly or via `uv run`).
