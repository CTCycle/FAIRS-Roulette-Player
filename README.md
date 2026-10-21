# FAIRS: Fabulous Automated Intelligent Roulette System

<p align="center"><img src='app/client/public/roulette_wheel.png' alt='FAIRS roulette wheel mark' width="112"></p>

**A local research workspace for roulette training experiments and step-by-step inference sessions.**


[![License](https://img.shields.io/github/license/CTCycle/FAIRS-Roulette-Player?style=flat-square)](LICENSE) [![Release](https://img.shields.io/github/v/release/CTCycle/FAIRS-Roulette-Player?display_name=tag&style=flat-square)](https://github.com/CTCycle/FAIRS-Roulette-Player/releases) [![CI](https://img.shields.io/github/actions/workflow/status/CTCycle/FAIRS-Roulette-Player/ci.yml?branch=develop&label=CI&style=flat-square)](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/workflows/ci.yml?query=branch%3Adevelop) [![Python](https://img.shields.io/badge/Python-3.14.7-3776AB?logo=python&logoColor=white&style=flat-square)](https://www.python.org/) [![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black&style=flat-square)](https://react.dev/) [![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white&style=flat-square)](https://www.microsoft.com/windows)

> FAIRS is an experimental research tool. Its suggestions are not guaranteed predictions or gambling advice. Roulette outcomes remain uncertain, and results from a simulation may not generalize to new data or future play.

## Overview

FAIRS is a local browser-based workspace for preparing roulette data, training an agent, saving checkpoints, and reviewing model suggestions against observed outcomes. It models a single-zero wheel with outcomes from 0 through 36.

## Key Features

- Import CSV or XLSX datasets and preview them, or generate synthetic data for repeatable experiments.
- Configure and monitor training runs, review their metrics, and save or resume checkpoints.
- Pair a checkpoint with a dataset and step through inference one round at a time.
- Record observed outcomes and review predictions, bets, capital, results, and session history.
- Use SQLite by default or configure an external PostgreSQL database.

## Screenshots

![Training workspace](assets/figures/training-page.png)

![Inference session](assets/figures/inference-page.png)

The screenshots show example interface states. Results and charts depend on the selected data, checkpoint, and run settings.

## Technology Stack

- Python 3.14.7 and FastAPI backend.
- React 19, TypeScript, and Vite web client; the launcher provisions Node.js 22.13.0.
- SQLite by default, with PostgreSQL available for advanced setups.
- Windows launcher with portable Python, uv, and Node.js runtimes.

## Installation and Usage

Windows is the supported launch environment. Extract the repository into a writable folder, open PowerShell at its root, and run:

```powershell
.\start_on_windows.ps1
```

Choose **Launch application**. On first use, the launcher prepares the local runtimes, dependencies, and database. Internet access is required to download missing runtimes and packages. The interface is designed for desktop browser windows at least 1100 pixels wide; mobile layouts are not supported.

## Configuration

The launcher creates `settings/.env` from `settings/.env.example` when needed. Set the API proxy target, listener hosts and ports, or optional CORS origins there before launch; these deployment values are separate from the user preferences saved by the Settings page. FAIRS stores local datasets, checkpoints, and logs under `data` by default; set `FAIRS_DATA_DIR` to choose another persistent data root. Training and inference preferences are available in the application.

## Documentation

- [Quick Start](assets/docs/operations/quick_start.md)
- [Training and inference workflows](assets/docs/operations/workflows.md)
- [Runtime startup](assets/docs/runtime/startup.md)
- [Runtime configuration](assets/docs/runtime/configuration.md)
- [Troubleshooting](assets/docs/operations/troubleshooting.md)

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
