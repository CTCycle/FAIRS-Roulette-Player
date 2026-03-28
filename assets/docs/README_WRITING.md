# README Writing Guidelines

This document defines required standards for `README.md` updates in this repository.

Goal: keep README user-focused, accurate, and consistent with the runtime/architecture docs in `assets/docs`.

## 1. Scope and Audience

README content must prioritize end users and maintainers operating the app, not internal implementation details.

Keep explanations focused on:

- what the project does,
- how to run it,
- how to package/distribute it,
- how to test it.

## 2. Required Consistency Checks

Any README update must stay coherent with:

- `assets/docs/ARCHITECTURE.md`
- `assets/docs/PACKAGING_AND_RUNTIME_MODES.md`
- `assets/docs/GUIDELINES_TESTS.md`
- actual scripts/commands in repository (`FAIRS/start_on_windows.bat`, `tests/run_tests.bat`, `release/tauri/build_with_tauri.bat`)

If behavior changed, update both README and affected docs in the same change.

## 3. Recommended README Structure

Adapt section numbering as needed, but keep this high-level flow:

1. Project overview
2. Model/dataset notes (if relevant)
3. Runtime modes (local + packaged desktop)
4. Mode switching and configuration
5. Setup/use workflow
6. Testing
7. Setup and maintenance scripts
8. Resource/runtime directories
9. Screenshots (if UI exists)
10. License

## 4. Content Rules

- Do not document internal function/class-level implementation.
- Use commands that actually work in this repo.
- Avoid speculative claims (only document observed behavior).
- Keep steps concise and reproducible.
- Use fenced command blocks for runnable commands.

## 5. Runtime and Packaging Accuracy

README must clearly state:

- active runtime profile file (`FAIRS/settings/.env`)
- available profile templates
- local launch command
- packaged desktop build command
- output artifact directories

Do not imply users must manually set internal runtime flags that are injected by Tauri (for example `FAIRS_TAURI_MODE`).

## 6. Testing Section Requirements

Include at least:

- primary test command (`tests/run_tests.bat`)
- optional manual pytest commands
- prerequisites when tests depend on optional runtime extras

## 7. Screenshot Guidance

If screenshots are present:

- store under project assets folder,
- use relative markdown paths,
- include short functional captions,
- remove/update stale captures when major UI changes land.

## 8. Quality Bar

A valid README update is:

- coherent with `assets/docs`,
- executable as written,
- minimal but complete for setup and usage,
- maintained alongside behavior changes.
