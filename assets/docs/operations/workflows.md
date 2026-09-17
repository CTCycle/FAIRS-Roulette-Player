## Workflows

Last updated: 2026-09-17

## Training Workflow

1. Open `Training`.
2. Upload a roulette dataset such as `CSV` or `XLSX`, or start the synthetic generator from the dataset preview. CSV delimiters are detected automatically for comma-, semicolon-, tab-, and pipe-separated files.
3. Open training configuration and work through the six sections: Agent Configuration, Environment & Memory, Bet Strategy Policy, Dataset Configuration, Session & Compute, and Summary.
4. Use the wizard breadcrumbs to revisit a section, confirm the summary, and start training.
5. Monitor status, episode/step progress, loss/RMSE, validation metrics, reward, capital, current bet, strategy, epsilon, replay-buffer warm-up, and history charts.
6. Review generated checkpoints from the checkpoint preview. Inspect metadata, open a checkpoint in Inference, resume training, or delete an obsolete checkpoint. When at least two checkpoints exist, choose **Compare** to open a modal with a side-by-side view of their stored configuration and final training summaries. A cancelled run is shown as stopped/cancelled and does not become a completed checkpoint.

If the workflow is unfamiliar, open Help and choose the Training walkthrough for a short guided tour. It can be dismissed at any time with the X button and can later be reopened from Tips & Tricks.

Stored-dataset subsampling selects a deterministic contiguous window instead of randomly reordering rows. This preserves roulette sequence adjacency before the chronological train/validation split. The split seed controls data-window selection; `training_seed` controls model initialization, agent exploration/replay randomness, and environment random starts.

The dashboard calls the period before the replay buffer is ready `Replay warm-up`. This is distinct from epsilon-greedy exploration, which can continue after replay training begins. Validation values appear only for fresh validation measurements.

## Resume Training Workflow

1. Open `Training`.
2. Select an existing checkpoint and use its resume action.
3. Complete the resume wizard and submit the run.
4. Monitor progress until completion or cancellation.

Resume uses the same train/validation environment construction as initial training. If the checkpoint configuration includes a validation split, resumed training therefore produces fresh validation measurements rather than carrying forward stale values.

## Checkpoint To Inference Workflow

1. Open `Training` and locate the checkpoint.
2. Use `Open in Inference`.
3. FAIRS verifies that the dataset recorded by the checkpoint is still available and supports the checkpoint perceptive field.
4. If the original dataset is valid, FAIRS opens Inference with the checkpoint, dataset, initial capital, and bet context preselected.
5. If the dataset is missing or incompatible, FAIRS does not silently substitute another dataset. Open Inference and choose the alternative dataset explicitly so the changed experimental context is visible.

## Inference Workflow

1. Open `Inference`.
2. Select a trained checkpoint and dataset, or upload an inference dataset.
3. Set initial capital and bet amount, then start an inference session.
4. Review the agent suggestion and apply its suggested bet when appropriate.
5. Step through rounds in the session history, entering or modifying observed values as needed.
6. Review the session history and use **Stop** to shut down the active session. After it stops, use **Clear** to delete the persisted step rows and return to a fresh setup. Navigation away from Inference and back restores an active session while the local backend session still exists; a backend restart ends process-local live sessions.

Dynamic betting strategies show the strategy name, current bet, and suggested next bet with each prediction. **Apply Suggested Bet** updates the current bet only; it does not submit an observation or advance the round.

For a new session, open Help and choose the Inference walkthrough if the setup-to-observation loop needs a quick refresher. The walkthrough is optional and does not open automatically on every Inference visit.

## Guidance And Tips

- Open `Help` in the header for Tips & Tricks and optional walkthroughs.
- Dismiss a contextual tip with its close button when it is no longer useful; the choice is remembered locally for that guidance version.

## Dataset And Checkpoint Hygiene

- Use the dataset browsing UI to inspect uploaded or generated datasets.
- Remove obsolete datasets when they no longer serve the experiment lifecycle.
- Keep checkpoints and datasets aligned so inference runs use the intended training lineage.
- Delete dependent checkpoints before removing a dataset that is still referenced by a training lineage.
- Treat checkpoint comparison values as stored training summaries, not as a standardized benchmark. A controlled benchmark requires identical evaluation data and protocol.

## Day-To-Day Usage Patterns

- Use local startup for normal experimentation.
- Run tests before sharing behavior changes.

## Key Features

- Dataset upload and management for roulette series
- Sequence-preserving deterministic training subsampling
- Training start, resume, stop, and status workflows
- DQN epsilon and replay-buffer warm-up telemetry
- Fresh validation during initial and resumed training
- Checkpoint listing, metadata inspection, comparison, and deletion
- Dataset-provenance-safe checkpoint handoff to Inference
- Inference sessions with stepwise progression and context controls
- Synthetic dataset generation with the same canonical roulette outcome range as uploaded data
- Local-first web runtime

## Related Files

- Read `quick_start.md` for the launch entry points.
- Read `troubleshooting.md` for common workflow failures and recovery checks.
