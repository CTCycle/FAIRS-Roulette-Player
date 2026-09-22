# Tier 2 validation campaign: VAL-07 + VAL-08

Date: 2026-09-22  
Latest status: `VAL-07 VALIDATED`; `VAL-08 OPEN / PARTIAL`  
Branch: `develop`  
Original campaign HEAD recorded before testing: `fbd2f7adb818f8476c2bfbb22eb60aa21340df48`

## Scope and boundary

This campaign followed `Inspect -> Execute -> Observe -> Diagnose -> Fix -> Retest -> Regress -> Record` for the six-step Training wizard and a real short stored-dataset CPU training run. It did not extend into checkpoint-to-Inference provenance, which remains VAL-10/VAL-11 scope.

The execution profile was Windows, managed Python `3.14.7`, Node `22.13.0`, SQLite, CPU execution, one Uvicorn worker, and the supported desktop browser at ports `8890` and `8051`.

## Baseline

- The supported `./start_on_windows.ps1` option 1 path started the application. The launcher reused the managed runtimes and rebuilt the frontend after the remediation.
- `GET /api/health` returned `{"status":"ok","application":"FAIRS","version":"3.4.2"}`.
- Alembic reported `0002_rename_relative_preference (head)`.
- The backend command line contained `--workers 1`; the initial training status was idle with no active job.
- Dataset `5` remained `val00_training_lineage` with `120` rows.
- The initial checkpoint list contained only `val00_lineage_20260921`. That checkpoint was not modified or replaced.
- The Training page rendered the connected state, dataset 5 preview, and the baseline checkpoint. Focused browser coverage reported no page errors, console errors, or failed requests.

The launcher’s automatic browser handoff reported Windows access denied on this host. The supported option 13 cleanup path also returned access denied; after exact process-identity verification, only the FAIRS-owned launcher trees were stopped and ports `8890` and `8051` were rechecked. An unrelated TKBEN listener on port `5000` was left untouched.

## VAL-07: wizard and validation boundary

### Manual browser coverage

Both DatasetPreview entry paths were exercised:

| Entry path | Observed payload mode |
| --- | --- |
| Configure training with this dataset from dataset 5 | `dataset_id=5`, `use_data_generator=false` |
| Use generator | `dataset_id=null`, `use_data_generator=true` |

All six sections were reachable and revisitable: Agent Configuration, Environment & Memory, Bet Strategy Policy, Dataset Configuration, Session & Compute, and Summary. Next, Back, and breadcrumbs retained representative edits across navigation. The exercised dependent controls included dynamic betting, strategy model, fixed strategy, bet unit/max overrides, GPU, and mixed precision. Summary values matched the selected values rather than defaults; generator Summary now also shows the selected generated-sample count.

Submission coverage confirmed `POST /api/training/validate` before `POST /api/training/start`. The valid browser regression compares the normalized `/validate` response with the payload sent to `/start` and confirms the stored-data mode mapping. Semantic validation remains authoritative in `TrainingConfig`; the React layer does not maintain a competing semantic rule set.

The following validation cases were exercised through the API contract and the browser boundary:

| Case | Result |
| --- | --- |
| `minimum_exploration_rate > exploration_rate` | rejected with 422 |
| `replay_buffer_size > max_memory_size` | rejected with 422 |
| `batch_size > replay_buffer_size` | rejected with 422 |
| strategy model enabled while dynamic betting is disabled | rejected with 422; browser controls also prevent the invalid combination |
| enabled `bet_max < bet_unit` | rejected with 422 |
| stored-data mode without `dataset_id` | rejected with 422 |
| invalid checkpoint identifier | rejected with 422 |
| representative numeric schema minimum and maximum breaches | rejected with 422 |
| valid stored CPU configuration | `/validate` succeeded and start became possible |

Invalid wizard submission remained open, displayed an actionable server error, and did not issue `/api/training/start`.

### VAL-07 regression

`app/tests/e2e/test_app_flow.py -k TrainingWizard -v`: **4 passed, 13 deselected**.

The focused `TestTrainingWizardFlow` group covers stored-dataset entry, generator distinction, six-step navigation/state retention, dependent controls, Summary mapping, invalid-submit prevention, validate-before-start ordering, and browser page/console/request failure collection.

### VAL-07 defect and remediation

- `VAL07-001` — Product defect. Reproduction: enter generator mode, change generated samples, and open Summary; the selected count was absent. Root cause: `DatasetPreview.tsx` built Summary rows without the generator-specific `numGeneratedSamples` value. Fix: add the conditional Generated Samples row in the owning component. Regression: `test_generator_entry_has_distinct_mode_and_summary_values`.

## VAL-08: real training, telemetry, and checkpoint publication

The canonical configuration reused the VAL-00 stored dataset and short CPU parameters: one episode, 100 maximum steps, perceptive field 8, batch/replay/max memory 100, `dataset_id=5`, `use_data_generator=false`, CPU, and mixed precision disabled. The tested revision suffix was `fbd2f7a`.

The first browser run (`4813930e`, checkpoint `val08_lineage_fbd2f7a`) completed, but exposed a product telemetry defect: the worker result contained final loss/RMSE while the dashboard’s authoritative completed status still displayed `N/A`. It was retained only long enough to diagnose and was not accepted as the final VAL-08 result.

After the backend fix, the browser wizard started `b6e428c3` with checkpoint `val08_lineage_fbd2f7a_fix`. The job reached `completed` and 100%; the browser showed `Training completed`, final `LOSS 1.796`, `RMSE 1.340`, episode 1/1, step 99/100, replay warm-up 100/100, and the completed progress wheel. The job metadata reported `final_loss=1.795681357383728` and `final_rmse=1.340030312538147`.

Because the one-episode run completed too quickly for sustained polling observation, the documented observational rerun used the same configuration with only `episodes=5` and checkpoint `val08_lineage_fbd2f7a_obs`. This was explicitly an observational rerun, not a changed canonical setup. Job `f9eecb83` provided the following live evidence:

- Initial Replay warm-up: episode 1/5, step 0/100, replay `1/100`, epsilon `0.75`, loss/RMSE `N/A`.
- Training transition: episode 2/5, step 9/100, replay `100/100`, epsilon `0.7098`, loss `1.861`, RMSE `1.364`, with reward/capital and chart state updating.
- Later polling showed episode 2/5, step 32/100, epsilon `0.6325`, loss `1.640`, RMSE `1.281`.
- Final browser state: episode 5/5, step 96/100, replay `100/100`, epsilon `0.102`, progress `100%`, status `Completed`, loss `0.5614`, RMSE `0.7493`, total reward `-760`, capital `240`, strategy `Keep`.

While active, `/api/training/status` and `/api/training/jobs/f9eecb83` agreed on the running job and progress. At terminal state, the status endpoint correctly cleared the active `job_id` and reported `is_training=false` with completed latest stats; the known job endpoint retained `status=completed`, `progress=100.0`, and no error. Validation metrics remained `N/A` when the current telemetry sample had no fresh validation measurement; this was not treated as a failure.

Checkpoint publication was verified before cleanup:

- `GET /api/training/checkpoints` listed the expected checkpoint.
- Reloading the Training page without a backend restart listed the checkpoint in the checkpoint preview.
- Metadata for `val08_lineage_fbd2f7a_obs` reported dataset 5, episodes 5, perceptive field 8, batch size 100, `final_loss=0.5613923072814941`, and `final_rmse=0.749261200428009`.
- The filesystem payload was complete: `.complete`, `saved_model.keras`, and `configuration/configuration.json` were present. The persisted configuration was complete and consistent with dataset 5, stored-data mode, episodes 5, max steps 100, perceptive field 8, batch/replay/max memory 100, CPU, and mixed precision disabled.
- Backend logs recorded matching start and successful-completion events for `b6e428c3` and `f9eecb83`.

### VAL-08 defect and remediation

- `VAL08-001` — Product defect. Reproduction: complete a real training run and inspect the dashboard quality cards; loss/RMSE remained `N/A` although the worker result contained `final_loss` and `final_rmse`. Root cause: `TrainingService` projected terminal status/message/epoch but discarded the worker’s final metrics when updating authoritative `latest_stats`. Fix: merge finite final loss/RMSE into the completed projection for initial and resumed runs. Regression: `app/tests/unit/test_training_service.py` plus the real browser/API completion and metadata checks above.

- `TEST-HARNESS-001` — Test-only contract mismatch. The first version of the deterministic API regression expected percentage progress as `1.0` and expected the terminal `/api/training/status` to retain the completed job ID. The live contract is `100.0` percentage progress and a cleared active job ID after finalization, with the completed record retained at `/api/training/jobs/{job_id}`. The assertions were corrected; no product code change was required.

### Environment and test-harness findings

- `ENV-001` — The launcher’s best-effort automatic browser open and its non-elevated option 13 cleanup both returned Windows access denied. Exact FAIRS process trees were verified and stopped with the required host permission; this was not classified as a product defect.
- `ENV-002` — The canonical `runtimes/cache/pytest-tmp` cleanup returned Windows `WinError 5`. The standard runner result was kept separate from product status, and the equivalent full collection passed with a repository-local cache plus an isolated basetemp outside `runtimes/cache`.

The deterministic API regression uses a unique checkpoint name, waits for its exact job ID, requires `completed` and 100% progress, checks terminal status semantics, validates metadata and persisted configuration, and deletes only the checkpoint it created.

## Regression results

The results below are from the original campaign at the HEAD recorded above; current VAL-07 follow-up results are recorded at the end of this report.

| Gate | Result |
| --- | --- |
| Focused wizard browser slice | `4 passed, 13 deselected` |
| Training API slice | `21 passed` |
| Training service unit slice | `8 passed` |
| Frontend lint | passed |
| Frontend build | passed (`tsc -b && vite build`) |
| Canonical `cmd /c app\\tests\\run_tests.bat` | harness-limited: `178 passed, 8 skipped, 53 errors` during protected canonical cache cleanup (`WinError 5`) |
| Full pytest with repository-local cache and basetemp outside `runtimes/cache` | `231 passed, 8 skipped` |

The eight full-suite skips are the repository’s conditional PostgreSQL/inference capability cases. The canonical runner failure is an environment/test-harness limitation; the same 239-test collection passed with the established local-cache workaround and an isolated basetemp outside the canonical disposable cache.

The 239-test full collection completed immediately before the final representative schema-maximum case was added; the expanded `test_training_api.py` slice was then rerun independently and passed all 21 cases.

## Cleanup and closure

The disposable checkpoints `val08_lineage_fbd2f7a`, `val08_lineage_fbd2f7a_fix`, and `val08_lineage_fbd2f7a_obs` were deleted through the checkpoint API after evidence capture. Final checks confirmed:

- checkpoint list: `val00_lineage_20260921` only;
- dataset 5: `val00_training_lineage`, 120 rows;
- training: idle, no active job;
- Alembic: `0002_rename_relative_preference (head)`.

The known protected `app/tests/.pytest-tmp/full-suite` directory remained locked by Windows after the standard-runner attempt. It was not removed or permission-modified; the successful full regression used an isolated basetemp outside the canonical cache.

No inference run was performed in the original campaign. Its VAL-07/VAL-08 results remain historical; the latest scoped status and next action are recorded in the follow-up below.

## VAL-07 follow-up: persisted-resource preflight

This follow-up supersedes the original report's VAL-07 status for the current checkout. The earlier combined campaign above ran at `fbd2f7adb818f8476c2bfbb22eb60aa21340df48`. The focused follow-up ran on `develop` with base HEAD `2517bc8a6bdc6ec5537bc799e50d272a7f732418`; the binary source/test patch from that base has Git object ID `ab918c7224fa27fe12c02f552dc5a08a2bceadd3`. The patch ID covers the three changed backend files and three changed Python test files. No product or test source changed after these final runs.

The environment was Windows, application `3.4.2`, Python `3.14.7`, SQLite, CPU, one backend worker, and the official local services on ports `8890` and `8051`. The launched app used repository Node `22.13.0`. Frontend lint/build were run from `app/client` with the installed Node `22.23.1`; the production build completed through `tsc -b && vite build` and transformed 1,771 modules.

### Current-revision scenarios and results

- The six-step wizard was manually traversed with persisted dataset 5, including forward/back navigation, revisiting steps, retained values, dependent controls, and Summary review. The wizard was closed without submitting.
- The focused browser regression proved `/api/training/validate` precedes `/api/training/start`, compared the normalized validation response to the submitted payload, and checked that a blank required episode value receives `422` without a start request.
- The API suite covered representative malformed/incompatible values and numeric boundaries; missing dataset configuration; a never-existing dataset ID with repeatable validation errors and no job/checkpoint side effects; and a dataset deleted after successful validation, rejected by `/start` with `404` and no job/checkpoint side effects. Direct `/start` with invalid semantic values returned `422` without creating a job/checkpoint. The existing missing-checkpoint resume case also passed.
- Service unit tests verified missing and wrong-kind stored datasets and an existing checkpoint output name are rejected before `start_job`.
- The API regression also completed its actual stored-dataset CPU run and checked terminal metrics and checkpoint metadata. This is API regression evidence only; the full VAL-08 browser telemetry campaign is not promoted by this follow-up.
- After the suite, the service was idle, checkpoint list contained only `val00_lineage_20260921`, and dataset 5 remained `val00_training_lineage` with 120 rows. The disposable dataset used for the delete-after-validation case was removed.

### Commands

Commands ran in PowerShell from the repository root. Pytest caches and basetemps were directed to `%TEMP%` to avoid the protected repository cache.

```powershell
$pytestRoot = Join-Path $env:TEMP 'fairs-val07-pytest'
& .\app\server\.venv\Scripts\python.exe -m pytest app/tests/e2e/test_training_api.py -q -o "cache_dir=$pytestRoot/cache" --basetemp "$pytestRoot/final-tmp"

$pytestRoot = Join-Path $env:TEMP 'fairs-val07-unit'
& .\app\server\.venv\Scripts\python.exe -m pytest app/tests/unit/test_training_service.py -q -o "cache_dir=$pytestRoot/cache" --basetemp "$pytestRoot/tmp"

$pytestRoot = Join-Path $env:TEMP 'fairs-val07-browser'
& .\app\server\.venv\Scripts\python.exe -m pytest app/tests/e2e/test_app_flow.py -k TrainingWizard -q -o "cache_dir=$pytestRoot/cache" --basetemp "$pytestRoot/tmp"

$env:RUFF_CACHE_DIR = Join-Path $env:TEMP 'fairs-val07-ruff-cache'
& .\app\server\.venv\Scripts\python.exe -m ruff check app/server/api/training.py app/server/app.py app/server/services/training.py app/tests/e2e/test_app_flow.py app/tests/e2e/test_training_api.py app/tests/unit/test_training_service.py

Push-Location app/client
npm run lint
npm run build
Pop-Location
```

| Check | Final result |
| --- | --- |
| `test_training_api.py` | `28 passed in 65.22s` |
| `test_training_service.py` | `11 passed in 5.82s` |
| `test_app_flow.py -k TrainingWizard` | `5 passed, 13 deselected in 11.41s` |
| Ruff on the six changed Python files | passed |
| Frontend `npm run lint` | passed |
| Frontend `npm run build` | passed (`tsc -b && vite build`) |
| Final health and cleanup | health `ok`; training idle; baseline checkpoint and dataset retained; ports `8890` and `8051` clear after stopping only verified FAIRS PIDs |

The first API rerun exposed a test-harness cleanup race: the prior start-while-running test ignored a stop wait that could time out, and the next start saw `409`. Its cleanup now requires the stop wait to complete before proceeding; the complete API file then passed all 28 tests. An earlier run with pytest's cache provider disabled also emitted an unknown `cache_dir` option warning; the final run kept the provider enabled and directed both cache and basetemp into `%TEMP%`, with no warning.

`VAL07-002` — Product defect fixed in this follow-up. Canonical validation and direct start did not preflight stored dataset existence/type or checkpoint output-name reuse. The shared service preflight now checks these resources before start creates a job, and `/training/validate` uses the same check. Regression evidence is the deleted-after-validation API case, stale-ID deterministic/no-side-effect case, and service-level missing/wrong-kind/checkpoint-collision tests.

**Current gate status:** `VAL-07` is `VALIDATED` for the supported Windows/SQLite/CPU profile on the source/test patch identified above. `VAL-08` remains `OPEN / PARTIAL` for the latest campaign state: the earlier browser telemetry evidence remains historical, and this follow-up did not repeat the complete browser-observed telemetry/checkpoint workflow. The standalone frontend test-script gap (`ISSUE-003`) and later campaign slices remain open.
