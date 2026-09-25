# VAL-18 CUDA, JIT, and Mixed-Precision Validation

- Date: 2026-09-23
- Branch: `develop`
- Tested source baseline: working tree based on `b66c89f` (`test: validate VAL-19 launcher maintenance`)
- Result: `VAL-18 VALIDATED` for the tested Windows CUDA profile

## Gate selection

VAL-18 was the next separately actionable gate after VAL-19. It covers CUDA device selection, mixed precision, and JIT compilation. The gate was exercised on the current implementation with a live dataset-backed training job. The conditional VAL-09 and VAL-20 triggers were also reviewed; the Windows JIT backend boundary was rechecked because it is adjacent to this hardware slice.

## Environment and isolation

- Windows 11 Pro, build 26200; managed Python 3.14.7; PyTorch 2.10.0+cu130 with CUDA 13.0.
- NVIDIA GeForce RTX 3060 Laptop GPU, driver 610.88, 6 GB VRAM, compute capability 8.6; one visible CUDA device.
- SQLite 3.50.4; one backend worker; standard runner services on ports 8890 and 8051.
- The database was backed up through SQLite's online backup API into `assets/QA/.scratch-val18-data`; it passed `PRAGMA integrity_check` and contained five datasets. The training job used stored dataset 5.
- The repository `.env` loader overrides inherited environment variables. For the successful run, `FAIRS_DATA_DIR` was temporarily set in `settings/.env`; that file was restored byte-for-byte (SHA-256 `A421DB30276B690D1AC14549AFCE9E850AF72533B95EBFF6FBC2DB42610EECDE`).

## Scenarios and results

The targeted standard-runner selection executed the new `test_val18_hardware.py` integration test plus the existing JIT Settings API tests.

The JIT result covers the supported Windows `eager` backend. No speedup or optimized-kernel performance claim is made; Windows `inductor` remains unavailable and was verified to reject cleanly.

| Scenario | Result |
| --- | --- |
| Select CUDA device 0 and mixed-float16 policy; reject device index 1 and reject CPU mixed precision. | Passed. |
| Enable `jit_compile=true` with the supported Windows `eager` backend and read the setting back before training. | Passed. |
| Reject Windows `inductor` while JIT is enabled; confirm HTTP 422 and that `eager` remains selected. | Passed. |
| Train one episode on dataset 5 with CUDA, device 0, mixed precision, and JIT enabled; wait for the real worker to finish. | Passed: job `9b2c072e`, checkpoint `val18_cuda_07d5583808`, `completed` at 100%. |
| Check finite final metrics, persisted device flags, complete-checkpoint marker, saved model, and worker logs. | Passed: loss `1.5457607507705688`, RMSE `1.2432862520217896`; worker logged `cuda:0` and the mixed-precision policy. The temporary checkpoint was removed after inspection. |

Verification summary:

- Standard runner live-server and frontend-bootstrap phases: `PASS`.
- Targeted Python selection: `3 passed, 97 deselected` in 34.24 seconds.
- `ruff check --no-cache app/tests/e2e/test_val18_hardware.py`: passed.
- `git diff --check`: passed.
- Frontend unit and E2E npm phases: `SKIPPED`; the package still defines neither script (ISSUE-003). This was an API/live-worker validation, not a visual browser pass or a full standard-suite run.
- Runner readiness printed the existing Windows redirected-input warnings; health checks passed and the live-server phase passed.

## Gate inventory after this pass

| Slice IDs | Current status | Notes |
| --- | --- | --- |
| VAL-00–VAL-08, VAL-10–VAL-19 | `VALIDATED` | Recorded in the canonical ledger for their tested profiles; VAL-18 is the result of this pass. |
| VAL-09, VAL-20 | Conditional and open | No VAL-09 trigger was found; the current VAL-20 Windows JIT boundary passed, but the full trigger/acceptance contract is not documented in the checked-in ledger/docs. |
| VAL-21, VAL-22 | Open validation debt | Malformed-input recovery, repetition, bounded performance, and state-leak detection remain unrun. |

No validation gate is currently `BLOCKED`. `frontend.workflows` remains `PARTIAL`, ISSUE-003 remains open, hosted PostgreSQL/ISSUE-002 remains validated/closed, `runtime.source-release` remains `WORKING`, and packaged artifacts remain `NOT_IMPLEMENTED`.

## Conditional gates and remaining debt

- VAL-09 remains conditional. No trigger was identified in the launcher-maintenance and hardware changes reviewed for this pass. Its exact trigger and acceptance criteria are not present in the checked-in ledger/docs, so no status promotion is inferred.
- VAL-20 remains conditional. The current Windows JIT boundary was rechecked: `eager` was accepted and used by the VAL-18 job; `inductor` was rejected as designed. The checked-in ledger/docs do not identify the full VAL-20 trigger or acceptance contract, so this adjacent evidence does not promote the whole gate.
- VAL-21 and VAL-22 remain unrun validation debt for malformed-input recovery, repetition, bounded performance, and state-leak detection. They form the next coherent resilience scope.
- `frontend.workflows` and the frontend script work were outside this hardware slice; additional browsers and physical-device behavior remain unvalidated here. ISSUE-003 remains open for the missing frontend test scripts.
- Hosted PostgreSQL 17.11 conformance remains validated by CI run `35879722209`; it was not rerun in this hardware slice. No gate is currently `BLOCKED`.

## Cleanup and final data check

- The canonical database and its disposable clone both passed `PRAGMA integrity_check`; both contained eight inference sessions and eight inference session steps after the run.
- The generated checkpoint, isolated data root, and isolated runner cache were removed. Ports 8051 and 8890 were clear after the runner finished.
- The two initial runner attempts skipped at the test's isolation guard because the blank repository dotenv value overrode the process-level root. They did not run the GPU scenario. The successful run used the corrected dotenv setup documented above.
