## Workflows

Last updated: 2026-07-20

## Training Workflow

1. Open `Training`.
2. Upload a roulette dataset such as `CSV` or `XLSX`, or use generated synthetic data when available.
3. Configure training inputs in the UI.
4. Start training.
5. Monitor progress, metrics, and status.
6. Review generated checkpoints from the checkpoint list.

The training wizard summarizes the selected dataset, checkpoint, strategy, betting, sampling, and compute settings before submission. The dashboard then displays live metrics and training history.

## Resume Training Workflow

1. Open `Training`.
2. Select an existing checkpoint.
3. Start resume training.
4. Monitor progress until completion or cancellation.

## Inference Workflow

1. Open `Inference`.
2. Select a trained checkpoint and the relevant dataset or session context.
3. Start an inference session.
4. Step through rounds with the available session actions.
5. Review prediction outcomes, rewards, and session state.
6. Shut down the session when finished.

## Dataset And Checkpoint Hygiene

- Use the dataset browsing UI to inspect uploaded or generated datasets.
- Remove obsolete datasets when they no longer serve the experiment lifecycle.
- Keep checkpoints and datasets aligned so inference runs use the intended training lineage.

## Day-To-Day Usage Patterns

- Use local startup for normal experimentation.
- Run tests before sharing behavior changes.

## Key Features

- Dataset upload and management for roulette series
- Training start, resume, stop, and status workflows
- Checkpoint listing, metadata inspection, and deletion
- Inference sessions with stepwise progression and context controls
- Local-first web runtime

## Related Files

- Read `quick_start.md` for the launch entry points.
- Read `troubleshooting.md` for common workflow failures and recovery checks.
