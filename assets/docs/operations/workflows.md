## Workflows

Last updated: 2026-08-02

## Training Workflow

1. Open `Training`.
2. Upload a roulette dataset such as `CSV` or `XLSX`, or start the synthetic generator from the dataset preview.
3. Open training configuration and work through the six sections: Agent Configuration, Environment & Memory, Bet Strategy Policy, Dataset Configuration, Session & Compute, and Summary.
4. Use the wizard breadcrumbs to revisit a section, confirm the summary, and start training.
5. Monitor status, progress, loss/RMSE, reward, capital, current bet, strategy, timestep, and history charts.
6. Review generated checkpoints from the checkpoint preview.

Synthetic training generates roulette `outcome` values in `0..36` and normalizes them to the training serializer's `extraction` field after wheel/color encoding. The dashboard displays live metrics and training history.

## Resume Training Workflow

1. Open `Training`.
2. Select an existing checkpoint and use its resume action.
3. Complete the resume wizard and submit the run.
4. Monitor progress until completion or cancellation.

## Inference Workflow

1. Open `Inference`.
2. Select a trained checkpoint and dataset, or upload an inference dataset.
3. Set initial capital and bet amount, then start an inference session.
4. Review the AI suggestion and apply its suggested bet when appropriate.
5. Step through rounds in the session history, entering or modifying observed values as needed.
6. Use Play, Stop, Clear, and session shutdown controls as the experiment requires.

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
- Synthetic dataset generation with the same canonical roulette outcome range as uploaded data
- Local-first web runtime

## Related Files

- Read `quick_start.md` for the launch entry points.
- Read `troubleshooting.md` for common workflow failures and recovery checks.
