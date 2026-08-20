# FAIRS: Fabulous Automated Intelligent Roulette System
Last updated: 2026-08-20

[![Release](https://img.shields.io/github/v/release/CTCycle/FAIRS-Roulette-Player?display_name=tag)](https://github.com/CTCycle/FAIRS-Roulette-Player/releases) [![Python](https://img.shields.io/badge/python-%3E%3D3.14-3776AB?logo=python&logoColor=white)](./app/server/pyproject.toml) [![Node.js](https://img.shields.io/badge/node.js-22.13.0-339933?logo=node.js&logoColor=white)](./start_on_windows.ps1) [![React](https://img.shields.io/badge/react-19.2.8-61DAFB?logo=react&logoColor=black)](./app/client/package.json) [![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![CI](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/workflows/ci.yml?query=branch%3Adevelop)
[![CTCycle Portfolio](https://img.shields.io/badge/CTCycle-Portfolio-58a6ff?style=flat-square)](https://ctcycle.github.io/CTCycle/)

FAIRS is a Windows-first local web workspace for roulette training and inference experiments. A FastAPI backend manages datasets, training jobs, checkpoints, inference sessions, and persistence while a React 19 + TypeScript frontend provides the interactive workspace.

FAIRS is an experimental research tool. Model suggestions are not guaranteed predictions, gambling advice, or a substitute for independent judgment.

## Requirements and assumptions

- Use a writable, extracted source repository on Windows with PowerShell. The launcher manages portable Python `3.14.2`, uv, and Node.js `22.13.0`; a separate global Python or Node.js installation is not required.
- The first setup needs outbound network access so the launcher can download runtimes and dependencies. Later starts reuse the prepared environment when its readiness checks pass.
- The normal runtime uses the CPU. GPU, mixed precision, and JIT options are available in the training wizard but require a compatible local ML environment.
- Roulette outcomes use the canonical single-zero range `0..36`. Inspect and validate uploaded CSV/XLSX data in the dataset preview before committing it to a training run.
- The web UI is desktop-only and requires a browser viewport at least 1100px wide. Phones and mobile layouts are unsupported; Windows tablets are supported only when they provide a normal desktop browser environment.

## What FAIRS helps with

- Import roulette datasets from CSV or XLSX files, or generate synthetic roulette data.
- Configure and start training through a six-section wizard with live metrics and history charts.
- Review checkpoints, resume training, and keep training artifacts aligned with their datasets.
- Pair a trained checkpoint with a dataset and step through an inference session.
- Review predictions, observed values, outcomes, capital, and session history in one view.
- Use SQLite by default or connect to PostgreSQL through explicit database configuration and initialization.

The backend is the source of truth for API behavior, background jobs, session state, and persisted data. The repository provides local web mode; it does not include a desktop installer, packaged executable, or supported container deployment.

## Get the source

The current source release is `v3.0.0`. Download a versioned source archive from the [GitHub Releases page](https://github.com/CTCycle/FAIRS-Roulette-Player/releases). FAIRS is intended for local launcher-based operation from an extracted repository.

## Set up and start the application

From the extracted repository root, open PowerShell and run:

```powershell
.\start_on_windows.ps1
```

On the first run, choose **2 — Install / update dependencies** if you want to prepare the environment explicitly. Select `Standard` for normal use or `Development` when you need the test dependencies. Then choose **1 — Launch application**. If the environment is missing, option 1 can prepare the Standard environment automatically.

The launcher creates `settings/.env` from `settings/.env.example` when needed, starts the FastAPI backend, and serves the built React frontend through Vite preview. Later starts reuse the environment when its readiness checks pass.

With the checked-in default settings, open:

- UI: `http://127.0.0.1:8051`
- API health: `http://127.0.0.1:8890/api/health`
- API documentation: `http://127.0.0.1:8890/docs`

The active ports come from `settings/.env`. The launcher also provides maintenance actions for dependency installation, database initialization, tests, logs, caches, and local runtime cleanup.

### Launcher menu

| Option | Use |
| --- | --- |
| `1` | Launch the backend and web UI. |
| `2` | Install or update dependencies; choose `Standard` or `Development`. |
| `3` | Rebuild the frontend from current source without updating dependencies. |
| `4` | Create or upgrade the configured database, including PostgreSQL. |
| `5` | Run the repository test suite. |
| `6` | Remove application log files. |
| `7` | Clear Python and uv caches. |
| `8` | Remove local runtimes and build outputs so the environment can be rebuilt. |
| `9` | Exit the launcher. |

## Tips & Tricks

Open **Help** from the Training or Inference workspace to see practical shortcuts and the optional walkthroughs. Tips & Tricks keeps the round-by-round inference loop, checkpoint reuse, synthetic-data setup, and baseline comparisons visible while you work.

![Tips & Tricks dialog](assets/figures/tips-and-tricks.png)
_Tips & Tricks brings workflow shortcuts and an optional Inference walkthrough into an active local inference workspace._

## Configure the runtime

Runtime configuration is split between these files:

- `settings/.env.example` — versioned environment template.
- `settings/.env` — local, ignored environment values created from the template when absent.
- `settings/configurations.json` — non-database technical settings such as job polling and device defaults.

Database settings belong in `settings/.env`; a `database` block in `configurations.json` is rejected.

### Database modes

- `EMBEDDED_DATABASE=true` uses SQLite. FastAPI startup and launcher option 4 run the shared Alembic create/upgrade runner against the configured database without resetting or repairing drift.
- `EMBEDDED_DATABASE=false` uses PostgreSQL. The runner first tries the configured target and creates it only when that connection returns SQLSTATE `3D000`; automatic creation requires `CREATEDB`. Target migrations use a transaction advisory lock.
- Empty databases upgrade to Alembic `head`. Exact unversioned legacy databases are stamped at `head` without recreating objects or changing rows. Partial, drifted, unknown, ahead, or multi-head states fail unchanged before services start.

### Database migration workflow

Alembic is the authoritative schema-evolution mechanism. The immutable baseline is under `app/server/alembic/versions/`; `app/server/alembic.ini` contains no credentials. From `app/server`, generate candidate revisions, review the generated operations manually, then check and apply them:

```powershell
uv run alembic -c alembic.ini revision --autogenerate -m "describe schema change"
uv run alembic -c alembic.ini check
uv run alembic -c alembic.ini current --check-heads
uv run alembic -c alembic.ini upgrade head
```

Use `uv run alembic -c alembic.ini upgrade head --sql` for offline SQL output. Future constraints must be explicitly named; existing unnamed foreign keys retain their current semantics and are not renamed for dialect-specific consistency. SQLite initialization serializes with `BEGIN IMMEDIATE` and PostgreSQL initialization uses deterministic advisory locks with bounded waits. Resolve lock timeouts or migration errors before retrying; automatic repair is intentionally disabled.

`FAIRS_DATA_DIR` can override the mutable database, logs, and checkpoint root. `FAIRS_LOG_DIR` can override the log directory for isolated runs.

## Training workflow

1. Open **Training**.
2. Upload a CSV/XLSX roulette dataset or start the synthetic generator.
3. Complete the six configuration sections: Agent Configuration, Environment & Memory, Bet Strategy Policy, Dataset Configuration, Session & Compute, and Summary.
4. Start training and monitor progress, loss/RMSE, reward, capital, current bet, strategy, timestep, and history charts.
5. Review generated checkpoints or resume an interrupted training run.

![Training workspace](assets/figures/training-page.png)
_The Training workspace combines dataset upload, checkpoint management, and a live training monitor with populated metrics and history charts._

Synthetic training generates roulette outcomes in the canonical `0..36` range and normalizes them for the training serializer.

## DQN overview

FAIRS trains a Deep Q-Network (DQN) agent. At each roulette step, the agent receives a fixed-length window of recent encoded outcomes plus the current normalized capital. The Q-network estimates the expected value of each available action. With probability `exploration_rate`, the agent tries a random action; otherwise it selects the action with the highest estimated value.

Each transition—state, action, reward, next state, and completion flag—is stored in replay memory. Once enough experience is available, training samples a random minibatch, computes a target from the observed reward plus the discounted value of the next state, and updates the online network with AdamW. The online network selects the next action while a separate target network evaluates it; the target network is periodically copied from the online network to make updates less volatile. Checkpoints include the model state and replay memory so training can be resumed. When dynamic betting uses a learned strategy, a second DQN follows the same pattern to select the strategy action.

### DQN parameters

The defaults below are the starting values in the Training wizard. Change one or two values at a time and compare training and validation metrics on the same dataset and seeds.

| Parameter | Default | Practical effect |
| --- | ---: | --- |
| `perceptive_field_size` | `64` | Number of recent outcomes in the state. Larger values provide more history but increase computation and may dilute useful signal. |
| `qnet_neurons` | `64` | Width of the main network layers. Larger values add capacity and can fit richer relationships, at the cost of time, memory, and possible overfitting. |
| `embedding_dimensions` | `200` | Size of the learned roulette-value representation. Larger values can represent more detail but increase model cost and overfitting risk. |
| `learning_rate` | `0.0001` | Size of each AdamW update. Higher values can learn faster but may make loss unstable; lower values are steadier but slower. |
| `batch_size` | `32` | Number of replay transitions used per update. Larger batches usually smooth updates but require more memory and compute; smaller batches are noisier and cheaper per update. |
| `discount_rate` | `0.50` | Weight given to future rewards (`gamma`). Higher values favor longer-term returns; lower values emphasize the immediate reward. |
| `exploration_rate` | `0.75` | Initial probability of a random action. Higher values explore more and delay early exploitation; lower values become greedy sooner. |
| `exploration_rate_decay` | `0.995` | Multiplicative reduction in exploration after replay. Values closer to `1` preserve exploration longer; smaller values reduce it faster. |
| `minimum_exploration_rate` | `0.10` | Lowest exploration probability. A higher floor keeps ongoing randomness; a lower floor produces a more deterministic final policy. |
| `replay_buffer_size` | `1000` | Experience threshold before replay begins and the replay-size cap used by the agent. Larger values delay the first updates but provide a broader warm-up pool. |
| `max_memory_size` | `10000` | Maximum number of transitions retained. Larger memory preserves more experience but uses more RAM and can keep older behavior longer. |
| `model_update_frequency` | `10` steps | How often the target network copies the online network. Smaller values track new learning more closely; larger values make targets more stable but potentially stale. |

`episodes` and `max_steps_episode` set the total training budget, not the DQN update rule. Increasing them gives the agent more opportunities to learn but takes longer. Keep `training_seed`, dataset selection, and validation split fixed when comparing parameter changes. Lower loss or a favorable simulated capital curve is evidence only for that dataset and experiment; it is not proof of a reliable roulette advantage.

## Inference sessions

1. Open **Inference**.
2. Select a trained checkpoint and dataset, or upload an inference dataset.
3. Set the initial capital and bet amount, then start the session.
4. Review the AI suggestion and apply it when appropriate for the experiment.
5. Step through rounds, enter or edit observed values, and review the session history.
6. Use **Play**, **Stop**, **Clear**, and session shutdown controls as needed.

![Inference session](assets/figures/inference-page.png)
_The Inference workspace pairs a trained checkpoint and dataset with live stepwise predictions, observed outcomes, and session history._

## Testing

Run the repository test entry point from the root:

```cmd
app\tests\run_tests.bat
```

Use launcher option 2 with `Development` selected before running tests if the test extra has not been installed.

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
- [`assets/docs/architecture/findings_and_remediation.md`](assets/docs/architecture/findings_and_remediation.md) — current architecture findings, target state, and prioritized remediation.

## License

FAIRS is licensed under the MIT License. See [`LICENSE`](LICENSE) for the terms.
