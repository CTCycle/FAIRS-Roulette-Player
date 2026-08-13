# FAIRS: Fabulous Automated Intelligent Roulette System
Last updated: 2026-08-13

[![Release](https://img.shields.io/github/v/release/CTCycle/FAIRS-Roulette-Player?display_name=tag)](https://github.com/CTCycle/FAIRS-Roulette-Player/releases) [![Python](https://img.shields.io/badge/python-%3E%3D3.14-3776AB?logo=python&logoColor=white)](./app/server/pyproject.toml) [![Node.js](https://img.shields.io/badge/node.js-22.13.0-339933?logo=node.js&logoColor=white)](./start_on_windows.ps1) [![React](https://img.shields.io/badge/react-19.2.0-61DAFB?logo=react&logoColor=black)](./app/client/package.json) [![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![CI](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/workflows/ci.yml?query=branch%3Adevelop)
[![CTCycle Portfolio](https://img.shields.io/badge/CTCycle-Portfolio-58a6ff?style=flat-square)](https://ctcycle.github.io/CTCycle/)

FAIRS is a Windows-first local web workspace for roulette training and inference experiments. A FastAPI backend manages datasets, training jobs, checkpoints, inference sessions, and persistence while a React 19 + TypeScript frontend provides the interactive workspace.

FAIRS is an experimental research tool. Model suggestions are not guaranteed predictions, gambling advice, or a substitute for independent judgment.

## What FAIRS helps with

- Import roulette datasets from CSV or XLSX files, or generate synthetic roulette data.
- Configure and start training through a six-section wizard with live metrics and history charts.
- Review checkpoints, resume training, and keep training artifacts aligned with their datasets.
- Pair a trained checkpoint with a dataset and step through an inference session.
- Review predictions, observed values, outcomes, capital, and session history in one view.
- Use SQLite by default or connect to PostgreSQL through explicit database configuration and initialization.

The backend is the source of truth for API behavior, background jobs, session state, and persisted data. The repository provides local web mode; it does not include a desktop installer, packaged executable, or supported container deployment.

## Get the source

The current source release is `v2.7.0`. Download a versioned source archive from the [GitHub Releases page](https://github.com/CTCycle/FAIRS-Roulette-Player/releases). FAIRS is intended for local launcher-based operation from an extracted repository.

## Start the application

From the repository root, open PowerShell and run:

```powershell
.\start_on_windows.ps1
```

On first use, the launcher creates `settings/.env` from `settings/.env.example` when needed, prepares the portable runtimes, installs dependencies, builds the frontend, and starts the FastAPI backend with the Vite preview server. Later starts reuse the environment when its readiness checks pass.

With the default settings, open:

- UI: `http://127.0.0.1:8001`
- API health: `http://127.0.0.1:8000/api/health`
- API documentation: `http://127.0.0.1:8000/docs`

The active ports come from `settings/.env`. The launcher also provides maintenance actions for dependency installation, database initialization, tests, logs, caches, and local runtime cleanup.

## Configure the runtime

Runtime configuration is split between these files:

- `settings/.env.example` — versioned environment template.
- `settings/.env` — local, ignored environment values created from the template when absent.
- `settings/configurations.json` — non-database technical settings such as job polling and device defaults.

Database settings belong in `settings/.env`; a `database` block in `configurations.json` is rejected.

### Database modes

- `EMBEDDED_DATABASE=true` uses SQLite. The application creates the configured database only when the file is missing and does not reset an existing database during normal startup.
- `EMBEDDED_DATABASE=false` uses PostgreSQL. Normal startup performs a non-mutating connection check. Use the launcher’s `Initialize database` option to create or initialize the database explicitly.

`FAIRS_USER_DATA_DIR` can override the mutable database, logs, and checkpoint root. `FAIRS_LOG_DIR` can override the log directory for isolated runs.

## Training workflow

1. Open **Training**.
2. Upload a CSV/XLSX roulette dataset or start the synthetic generator.
3. Complete the six configuration sections: Agent Configuration, Environment & Memory, Bet Strategy Policy, Dataset Configuration, Session & Compute, and Summary.
4. Start training and monitor progress, loss/RMSE, reward, capital, current bet, strategy, timestep, and history charts.
5. Review generated checkpoints or resume an interrupted training run.

![Training workspace](assets/figures/training-page.png)
_The Training workspace combines dataset upload, checkpoint management, and the live training monitor._

Synthetic training generates roulette outcomes in the canonical `0..36` range and normalizes them for the training serializer.

## Inference sessions

1. Open **Inference**.
2. Select a trained checkpoint and dataset, or upload an inference dataset.
3. Set the initial capital and bet amount, then start the session.
4. Review the AI suggestion and apply it when appropriate for the experiment.
5. Step through rounds, enter or edit observed values, and review the session history.
6. Use **Play**, **Stop**, **Clear**, and session shutdown controls as needed.

![Inference session](assets/figures/inference-page.png)
_The Inference workspace pairs checkpoint and dataset setup with stepwise predictions and session history._

## Testing

Run the repository test entry point from the root:

```cmd
app\tests\run_tests.bat
```

For focused backend runs, enter the server project directory and target the relevant suite:

```powershell
Push-Location app/server
uv run pytest -q ../tests/unit
uv run pytest -q ../tests/e2e
Pop-Location
```

## Documentation

Start with [`assets/docs/project_index.md`](assets/docs/project_index.md), then use the focused guides:

- [`assets/docs/operations/quick_start.md`](assets/docs/operations/quick_start.md) — fastest launch path.
- [`assets/docs/operations/workflows.md`](assets/docs/operations/workflows.md) — training and inference sequences.
- [`assets/docs/operations/troubleshooting.md`](assets/docs/operations/troubleshooting.md) — recovery checks.
- [`assets/docs/runtime/startup.md`](assets/docs/runtime/startup.md) — launcher behavior and database lifecycle.
- [`assets/docs/runtime/configuration.md`](assets/docs/runtime/configuration.md) — environment and settings.
- [`assets/docs/architecture/system_overview.md`](assets/docs/architecture/system_overview.md) — source tree and runtime surfaces.

## Training demo

The repository also includes a short training animation:

![Training demo](assets/training_demo.gif)
_DQN agent learning roulette over 30 episodes with epsilon-greedy exploration and decay._

## License

FAIRS is licensed under the MIT License. See [`LICENSE`](LICENSE) for the terms.
