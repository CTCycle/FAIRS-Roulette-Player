## Project Overview

Last updated: 2026-08-30

## Purpose

This file is the root index for `assets/docs`.
Read it first, then open the smallest leaf document that matches the task.

The documentation set is synchronized with the current codebase: local Windows web runtime, portable Python `3.14.2`, Node.js `22.13.0`, FastAPI backend, and React/Vite frontend. The authoritative backend application version is `app/server/pyproject.toml`.

## Navigation Rules

1. Start with this file only.
2. Pick the topic branch that matches the request.
3. Open the narrowest leaf file in that branch.
4. Read sibling files only when the task crosses boundaries.
5. Return here when you need to switch topics.

## Naming Rules

- All files and folders under `assets/docs` use lower-case names.
- Root-level files are reserved for entry points and high-level guidance.
- Topic folders contain narrowly scoped leaf files.
- Each documentation file must keep a `Last updated: YYYY-MM-DD` line.

## Documentation Ontology

### Root

- `project_index.md`
  - Master index, navigation rules, and documentation handling policy.

### Architecture

- `architecture/system_overview.md`
  - Repository layout, runtime components, entry points, and frontend structure.
- `architecture/backend_api.md`
  - Mounted routers, endpoint catalog, and API interaction boundaries.
- `architecture/execution_and_data_flow.md`
  - Backend layering, orchestration chains, core module responsibilities, and concurrency model.
- `architecture/persistence.md`
  - Database backends, tables, persisted files, and runtime storage surfaces.
- `architecture/findings_and_remediation.md`
  - Evidence-backed architecture findings, target state, and prioritized remediation roadmap.

### Coding

- `coding/python.md`
  - Python runtime baseline, typing, validation, async, persistence, and structure rules.
- `coding/typescript.md`
  - TypeScript architecture, React patterns, frontend state, and UI implementation rules.
- `coding/testing_and_quality.md`
  - Testing layout, linting, type discipline, and change-quality expectations.
- `coding/windows_automation.md`
  - PowerShell conventions for the Windows-first launcher and its helper scripts.

### Runtime

- `runtime/modes.md`
  - Supported runtime modes and how they differ.
- `runtime/startup.md`
  - Local startup, maintenance, and test commands.
- `runtime/configuration.md`
  - Environment variables, runtime flags, and structured settings files.
- `runtime/deployment.md`
  - Local distribution boundaries and operational constraints.

### UI

- `ui/design_tokens.md`
  - Typography, spacing, radius, and color tokens.
- `ui/components_and_patterns.md`
  - Navigation, cards, forms, buttons, overlays, and interaction states.
- `ui/experience.md`
  - Page composition, workflow behavior, responsiveness, accessibility, and design principles.

### Operations

- `operations/quick_start.md`
  - Fastest path to launch the application and orient a new operator.
- `operations/workflows.md`
  - Primary training and inference user journeys plus day-to-day usage patterns.
- `operations/troubleshooting.md`
  - High-signal checks for startup, API docs, tests, and runtime mismatches.

## Reading Paths By Task

- For repository structure, routes, or data flow:
  - start in `architecture/`
- For implementation standards:
  - start in `coding/`
- For launchers, environment, or local distribution:
  - start in `runtime/`
- For frontend design behavior:
  - start in `ui/`
- For operator guidance:
  - start in `operations/`

## Context Rules

- Read documentation only when required by the current task.
- Prefer the smallest leaf file that answers the question.
- Keep all affected docs updated in the same change when implementation changes alter behavior.
- When launcher, schema, API, or UI behavior changes, update the corresponding architecture, runtime, operations, and UI leaf documents together.
- Use folder structure, file names, routes, tests, and imports to pre-select docs before opening them.
- Do not read the entire documentation tree unless the task explicitly requires broad context.

## Environment Rules

- Windows is the default operating environment for this repository.
- PowerShell is the default interactive shell for analysis and automation.
- `start_on_windows.ps1` is the single interactive startup and maintenance entry point.
- Command examples should use PowerShell unless CMD materially improves usability.
