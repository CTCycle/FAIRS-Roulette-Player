You are working on the FAIRS-Roulette-Player repository checked out at the current directory.

TASK: Remove all Tauri packaging infrastructure, consolidate the launcher scripts into a single PowerShell menu, and update all documentation. Do NOT modify any Python, TypeScript, or Angular source code.

## Note: This repo does NOT have an app/src-tauri/ directory — only the Tauri build scaffolding exists.

## Step 1: Create `app.ps1` at repo root

Replace both `start_on_windows.bat` and `setup_and_maintenance.bat` with a single `app.ps1` interactive menu.

Menu title: "FAIRS — Roulette Player"

The menu options and logic are identical to PROMPT 1 Step 1. Read the existing batch files in this repo for exact paths, ports, and defaults.

## Step 2: Delete old batch files

- start_on_windows.bat
- setup_and_maintenance.bat

## Step 3: Delete Tauri scaffolding

Directories to delete (entire trees):
- release/tauri/ (build_with_tauri.bat, scripts/clean-tauri-build.ps1, scripts/export-windows-artifacts.ps1)
- release/windows/ (if exists)

Files to delete:
- .github/workflows/desktop-release.yml

## Step 4: Update .gitignore

Remove any Tauri entries.

## Step 5: Update README.md

Read the current README.md and make these changes:
- Remove "An optional Tauri desktop shell for packaged Windows distribution" from the overview
- Remove the entire "Desktop Mode (Tauri Packaging)" subsection
- Remove "release\tauri\build_with_tauri.bat" and "release/windows/installers|portable" references
- Remove the paragraph about app/src-tauri versioned source (it doesn't exist)
- Remove "Optionally package a desktop build with Tauri when needed" from the usage section
- Update batch file references to app.ps1

## Step 6: Update assets/docs/

Scan for any Tauri references and update.

## Step 7: Verify

Check: release/tauri/ gone, desktop-release.yml deleted, app.ps1 exists, no Tauri references in docs.