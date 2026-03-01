## WEB SEARCH
Use web search when it materially improves accuracy for libraries, tools, standards, or external behavior assumptions.

## REQUIRED RULE REVIEW
Before starting work, review `.agent/rules` files relevant to the task:

- `GENERAL_RULES.md` (always)
- `ARCHITECTURE.md` (system structure and APIs)
- `BACKGROUND_JOBS.md` (when touching async/background flows)
- `GUIDELINES_PYTHON.md` (Python/backend work)
- `GUIDELINES_TYPESCRIPT.md` (frontend/TypeScript work)
- `GUIDELINES_TESTS.md` (tests)
- `PACKAGING_AND_RUNTIME_MODES.md` (runtime/deployment changes)
- `README_WRITING.md` (README authoring/updates)

## DOCUMENTATION UPDATES
If behavior, architecture, runtime, or developer workflow changes, update the affected `.agent/rules` documents in the same task and mention it in the final summary.

## CROSS-LANGUAGE PRINCIPLES

### Code quality
- Keep naming explicit and domain-oriented.
- Prefer small, composable modules with clear responsibilities.
- Optimize for readability and maintainability over cleverness.

### Testing and automation
- Keep lint/type/test steps runnable and deterministic.
- Prefer tests that validate user-visible behavior and API contracts.

### Security
- Validate untrusted input at boundaries.
- Avoid leaking secrets in logs, code, or test fixtures.
- Keep exposed surface area minimal.

## EXECUTION RULES (WINDOWS)
- Use PowerShell for local command execution.
- Use `cmd /c` when invoking `.bat` flows or when command behavior requires CMD semantics.

## FILE CHANGE NOTICE
- Significant functional changes require corresponding updates to `.agent/rules` docs.
