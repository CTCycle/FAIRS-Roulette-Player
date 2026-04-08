# Documentation Rules

Last updated: 2026-04-08

## WEB SEARCH
Use web search only when it materially improves accuracy (for example, external tool behavior or version changes). Prefer repository source of truth for project-specific facts.

## REQUIRED DOCUMENTATION REVIEW
Before any task, review this file first, then only the minimum additional docs needed:

- `ARCHITECTURE.md`
- `BACKGROUND_JOBS.md`
- `GUIDELINES_PYTHON.md`
- `GUIDELINES_TESTS.md`
- `GUIDELINES_TYPESCRIPT.md`
- `PACKAGING_AND_RUNTIME_MODES.md`
- `USER_MANUAL.md`

## COMPLETE DOCUMENTATION INVENTORY (`assets/docs`)
The complete and exhaustive list of documentation files in this folder is:

- `ARCHITECTURE.md`
- `BACKGROUND_JOBS.md`
- `GENERAL_RULES.md`
- `GUIDELINES_PYTHON.md`
- `GUIDELINES_TESTS.md`
- `GUIDELINES_TYPESCRIPT.md`
- `PACKAGING_AND_RUNTIME_MODES.md`
- `USER_MANUAL.md`

If a file is added, removed, or renamed in `assets/docs`, update this list in the same change.

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
