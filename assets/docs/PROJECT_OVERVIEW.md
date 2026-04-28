# PROJECT OVERVIEW

Last updated: 2026-04-24

FAIRS (Fabulous Automated Intelligent Roulette System) is a Windows-first roulette research application composed of a FastAPI backend, a React + Vite frontend, and an optional Tauri desktop runtime.

## FILES INDEX

- PROJECT_OVERVIEW.md  
  Master documentation index and repository-level documentation handling rules.

- ARCHITECTURE.md  
  Full implementation architecture: source tree, API endpoints, entry points, layered flow, and persistence model.

- CODING_RULES.md  
  Consolidated coding and quality standards for Python and TypeScript used in this repository.

- RUNTIME_MODES.md  
  Supported execution modes, startup commands, configuration differences, interoperability, and deployment constraints.

- UI_STANDARDS.md  
  Enforceable UI system derived from current frontend implementation: tokens, components, accessibility, and responsive behavior.

- USER_MANUAL.md  
  Operator-focused guide for running the app and completing training/inference workflows.

## CONTEXT RULES

- Read documentation only when required by the task.
- Defer opening docs until a concrete question or implementation need appears.
- Keep all affected docs updated in the same change when behavior or structure changes.
- Always add or refresh a `Last updated: YYYY-MM-DD` line when modifying a doc.
- Do not read all `SKILL.md` files indiscriminately.
- Pre-select relevant files from folder structure, feature area, and user intent before reading.

## ENVIRONMENT RULES

- Windows is the default operating environment for this repository.
- Use PowerShell as the default interactive shell for analysis and automation.
- Use CMD for batch launchers and scripts (`*.bat`) when required by project tooling.
- Keep command examples for both PowerShell and CMD where it improves usability.
- Update these environment notes when new Windows-specific runtime/setup constraints are discovered.
