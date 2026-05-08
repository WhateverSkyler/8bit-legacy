# Shorts QA gates — regression tests

Self-contained test scripts for the 5-gate LLM QA system. Run from the repo root.

## Local-only tests (run with project's `.venv/bin/python3`)

```bash
# Plumbing — move_to_rejected, emit_reject_navi, emit_flag_navi, log_gate_decision
.venv/bin/python3 scripts/podcast/tests/test_reject_path.py

# Mock-driven rescue logic — Gate 2 offset rescue + Gate 3 stricter-detection rescue
# (uses fake Claude responses + fake rerender closures, no API cost)
.venv/bin/python3 scripts/podcast/tests/test_rescue_paths_mock.py

# Concurrent Gate 1 — verifies parallelization preserves order + correctness,
# proves wall-time speedup on 6 candidates with mocked 2s/call latency
.venv/bin/python3 scripts/podcast/tests/test_gate1_parallel.py

# End-to-end Gates 2→3→4 on a real May 5 clip (real Claude calls, ~$0.40)
# Requires /tmp/may5-test/ artifacts from prior debugging or pull from NAS
.venv/bin/python3 scripts/podcast/tests/test_e2e_gates234.py
```

## Container-only test (real ffmpeg required, libass not on Mac)

```bash
# Renders a 30s clip, mocks Claude to return rerender_with_offset(0.4),
# verifies the rescue closure actually rebuilds ASS + re-runs ffmpeg + re-calls Gate 2.
# Run via TrueNAS Tier-2 cronjob:
#   scp /tmp/test-rescue-in-container.py truenas_admin@192.168.4.2:/tmp/
#   docker run --rm --env-file /mnt/pool/apps/8bit-pipeline/.env \
#     -v /mnt/pool/apps/8bit-pipeline/data:/app/data \
#     -v /tmp/test-rescue-in-container.py:/app/test.py:ro \
#     --user 950:950 --entrypoint python3 8bit-pipeline:latest /app/test.py
scripts/podcast/tests/test_rescue_real_ffmpeg_container.py
```

## Validation history (2026-05-07 night)

| Test                                          | Pass/Total | Notes                                 |
|-----------------------------------------------|------------|---------------------------------------|
| `test_reject_path.py`                         | 21/21      | Plumbing                              |
| `test_rescue_paths_mock.py`                   | 25/25      | Logic                                 |
| `test_gate1_parallel.py`                      | 13/13      | Order + correctness preserved         |
| `test_rescue_real_ffmpeg_container.py`        | 7/7 G2 path | G3 path correctly bails when stricter detection finds same scenes |
| `test_e2e_gates234.py`                        | passes    | Gate 4 caught real title-content mismatch |

If any of these starts failing in the future, the QA pipeline is regressing.
