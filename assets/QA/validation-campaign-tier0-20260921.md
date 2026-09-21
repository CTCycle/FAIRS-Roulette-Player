# Validation campaign Tier 0 evidence

Date: 2026-09-21
Branch: `develop`
Source revision under test: working tree rooted at `f61507d846bcea5c3349c35041252ff5b4d539de`
Profile: Windows, managed Python `3.14.7`, SQLite, CPU, one backend worker
Configured ports: backend `8890`, frontend `8051`

## Result summary

| Slice | Result | Stable issue | Notes |
| --- | --- | --- | --- |
| `VAL-00` | `VALIDATED` | — | Real dataset upload, CPU training, checkpoint publication, metadata, database, and log evidence agree. |
| `VAL-01` | `VALIDATED` | — | Startup/browser, the corrected full-green zero sector, focused E2E checks, and the supported elevated launcher option 13 cleanup path all passed. |

## VAL-00 — deterministic real lineage

Pre-run state was SQLite Alembic head `0002_rename_relative_preference`, with no inference sessions and no checkpoint directories. Existing datasets were preserved. The fixture [`val00_training_lineage.csv`](val00_training_lineage.csv) contains 120 valid roulette outcomes and is now tracked with the QA evidence.

The official launcher option 1 started the application. The rendered Training route reached `Connected`, and the backend log recorded successful health and application requests. The fixture was uploaded through the real API:

```text
POST /api/data/upload?dataset_kind=training&csv_separator=%2C
200
filename=val00_training_lineage.csv
rows_imported=120
dataset_id=5
dataset_name=val00_training_lineage
```

A real CPU training job was then started against dataset `5` with one episode, 100 maximum steps, perceptive field `8`, batch/replay/memory size `100`, and checkpoint name `val00_lineage_20260921`:

```text
POST /api/training/start
202
job_id=fae03fc4
status=started

GET /api/training/jobs/fae03fc4
status=completed
progress=100.0
final_loss=4.52057409286499
final_rmse=2.126164197921753
checkpoint_path=app/resources/checkpoints/val00_lineage_20260921
```

Checkpoint and persistence checks after completion:

```text
GET /api/training/checkpoints
["val00_lineage_20260921"]

GET /api/training/checkpoints/val00_lineage_20260921/metadata
dataset_id=5
episodes=1
perceptive_field_size=8
final_loss=4.52057409286499
final_rmse=2.126164197921753

SQLite dataset_id=5: 120 outcomes
SQLite inference_sessions: 0
SQLite alembic_version: 0002_rename_relative_preference
```

The backend log recorded `Started training run fae03fc4` and `Training run fae03fc4 completed successfully`, with no error-level entry observed in the application log for this run. This closes the deterministic lineage prerequisite; live inference is intentionally the next slice (`VAL-11`), not part of VAL-00.

## VAL-01 — startup and shutdown smoke

The official launcher option 1 reported `[OK] FAIRS frontend is ready`, started the backend and frontend on the configured ports, and reported the expected URLs. Automatic browser handoff was denied by the desktop boundary, so the in-app browser opened the frontend directly at `/training`.

Rendered/browser evidence:

- page title: `FAIRS Roulette Player`;
- URL: `http://127.0.0.1:8051/training`;
- startup screen absent after health became ready;
- visible `Connected` state and Training navigation;
- the backend-wait wheel renders zero as a full green sector in the rotor, with no rectangular zero-pocket element;
- in-app browser console errors/warnings: none;
- the focused startup suite passed all five selected tests.

Focused command and result:

```text
app/server/.venv/Scripts/python.exe -m pytest app/tests/e2e/test_app_flow.py -k TestStartupFlow -v
5 passed, 7 deselected in 25.81s
```

The first non-elevated launcher menu option 13 returned `Accesso negato`. A permission-safe rerun through the official elevated launcher then completed its own confirmation/listing path, found nine FAIRS-owned application and child processes, stopped all nine, and confirmed:

```text
launcher option 13: [OK] Stopped 9 FAIRS application process(es).
remainingOwnedWrappers=0
remainingPorts=0
```

The earlier `ISSUE-004` (`test/environment problem`) is closed as an environment permission boundary; no launcher remediation was required.

The focused viewport screenshots were refreshed by this run and are the visual regression evidence for the full green zero sector.

## Tracked evidence

- [`val00_training_lineage.csv`](val00_training_lineage.csv) — deterministic 120-row training fixture.
- [`fairs_startup_loading_1100x800.png`](fairs_startup_loading_1100x800.png) — focused startup viewport evidence.
- [`fairs_startup_loading_1440x900.png`](fairs_startup_loading_1440x900.png) — focused startup viewport evidence.
- [`python314-migration-validation-20260921.md`](python314-migration-validation-20260921.md) — runtime and standard-runner baseline.
- [`startup-launch-smoke-20260920.md`](startup-launch-smoke-20260920.md) — prior launcher/browser smoke context.

## Tier 0 handoff

Tier 0 is closed. Continue with `VAL-02` and use dataset `5` plus checkpoint `val00_lineage_20260921` for `VAL-11`.
