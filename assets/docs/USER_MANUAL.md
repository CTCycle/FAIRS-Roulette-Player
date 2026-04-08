# FAIRS User Manual

Last updated: 2026-04-08

This manual explains how to run and use FAIRS for roulette dataset ingestion, training, and inference sessions.

## 1. Quick Start

1. From repository root, run:

```cmd
FAIRS\start_on_windows.bat
```

2. Open the UI in your browser at the configured frontend URL (`UI_HOST:UI_PORT` from `FAIRS/settings/.env`).
3. Use the navigation to move between:
- `Training`
- `Inference`

## 2. Primary Commands

### Start app (local mode)

```cmd
FAIRS\start_on_windows.bat
```

### Run full automated tests

```cmd
tests\run_tests.bat
```

### Build desktop package (Tauri)

```cmd
release\tauri\build_with_tauri.bat
```

### Optional cleanup / maintenance

```cmd
FAIRS\setup_and_maintenance.bat
```

## 3. Core User Journeys

### Journey A: Upload data and train a model

1. Go to `Training`.
2. Upload a roulette dataset (`CSV`/`XLSX`) or use generated synthetic sequences.
3. Configure training inputs in the UI.
4. Start training and monitor progress/status.
5. Review generated checkpoints from the checkpoints list.

### Journey B: Resume training from a checkpoint

1. Open `Training`.
2. Select an existing checkpoint.
3. Start resume training.
4. Monitor status until completion/cancellation.

### Journey C: Run inference session

1. Open `Inference`.
2. Select a trained checkpoint and a dataset/session context.
3. Start an inference session.
4. Step through rounds (`next`, `step`, or `bet` actions in UI workflow).
5. Review prediction outcomes, rewards, and session state.
6. Stop/shutdown session when done.

### Journey D: Manage datasets and history

1. Use dataset browsing UI to inspect uploaded/generated datasets.
2. Remove obsolete datasets when needed.
3. Keep checkpoints and datasets aligned with your experiment lifecycle.

## 4. Usage Patterns

- Use local mode (`start_on_windows.bat`) for day-to-day experimentation.
- Keep `FAIRS/settings/.env` as the active runtime profile for ports and runtime toggles.
- Use `tests\run_tests.bat` before sharing changes that affect behavior.
- Use Tauri packaging only when preparing distributable desktop builds.

## 5. Key Features

- Dataset upload and management for roulette series.
- Training start/resume/stop workflows with job status tracking.
- Checkpoint listing, metadata viewing, and checkpoint deletion.
- Inference sessions with stepwise progression and context controls.
- Local-first runtime and optional desktop packaging.

## 6. Troubleshooting Basics

- If app startup fails, rerun `FAIRS\start_on_windows.bat` to ensure runtimes/dependencies are in sync.
- If API docs are unavailable, check `ENABLE_API_DOCS` in `FAIRS/settings/.env`.
- If tests fail to start browsers, ensure optional dependencies are installed (`OPTIONAL_DEPENDENCIES=true`, then rerun launcher).
- If packaged app fails, verify Rust toolchain (`rustup default stable`) and rerun packaging helper.
