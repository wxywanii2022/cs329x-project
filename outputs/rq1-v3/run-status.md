# SC v3 execution — first smoke results and submitted jobs

> **Completion update (2026-11-18):** all listed jobs finished COMPLETED, exit 0,
> zero restarts. Every planned item outcome is present and all 15 new journals
> passed local/remote audit; no transport failure. The 27B v3 primary has coverage
> 59/60, κ 0.666 and FMR 2/55, versus the SC v2 control's 60/60, κ 0.652 and
> FMR 5/56. M1-009 exceeds the frozen v3 byte budget (200593 > 200000), so its
> failure remains unchanged. True reference zeros flagged: v3 1/4 vs v2-SC 2/4.
> See `report.md`, `completed-audit-and-comparison.json`, and the new v3 results
> section in `docs/local-assessor.md`. The text below is the preserved submission-time
> snapshot, not current job status. Result commit/push still requires approval.

This is an operational snapshot on 2026-11-17 PST, not the Main 1 result report.
The preregistration and seven supporting files were committed and pushed as
`d6e17c160d73bb98c5d51ec4a8e56154ce5253b0` with Yuan Tian's explicit approval,
then pulled and hash-verified on SC before the first v3 inference.
Primary rule: option (a), Qwen3.8-27B-FP8 seed 329.

## Environment

Setup job 18563751 completed on jagupard38 in 7m36s. Python 3.12.3,
vLLM 0.32.0, torch 2.13.0+cu130, CUDA runtime 13.0. RTX 6000 Ada,
49140 MiB reported by nvidia-smi, driver 610.43.02 (CUDA UMD 13.3).
CUDA tensor check and all 63 baseline tests passed on the worker. Local tests
of the committed additions: 71 passed, 2 skipped (73 total).

Both pinned HF snapshots were downloaded on scdt and their indexed shards
checked. Code, environment, caches and weights are on `/nlp/scr/yuantian`.
Observed filesystem capacity is 200 GB, about 60 GB used after setup/download.
Exact package versions, GPU information and snapshot paths are in `runtime/`.

## Real-model smoke results (synthetic only)

| Model | Slurm job | Valid | Failed | Pending | Long-item input tokens | Item latency range |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-FP8 | 18564163 | 5/5 | 0 | 0 | 53,829 | 13.446–53.899 s |
| Qwen3.5-9B | 18564495 | 5/5 | 0 | 0 | 53,791 | 43.353–72.597 s |

Both jobs ended COMPLETED with exit 0 (13m03s and 13m41s respectively,
including cold loading/compilation). Each produced three labels 2, one N/A and
one 0. Both raw journals were audited on the cluster and again after transfer
to the local repository; no output was repaired, relabeled or resampled.
This confirms operational validity/long-context completion, not human accuracy.

## Runtime observations to retain in the eventual results documentation

- Historical v1/v2 used FarmShare L40S; these v3 runs use SC RTX 6000 Ada.
- Cold NFS checkpoint loading took about 397 seconds for the first 27B server.
  A one-time allocated-node diagnostic showed page-IO wait, about 5.5 GB RSS
  and zero swap for its engine; this was not an observed OOM. No load-timeout
  increase, cache migration or model-parameter change was made.
- vLLM selected `MarlinFP8ScaledMMLinearKernel` for the 27B checkpoint's
  128x128 block-scaled FP8 weights. Its helper emits a generic warning about
  lack of native FP8 compute and weight-only Marlin execution. Report the
  actual selected backend rather than infer arithmetic from Ada hardware
  specifications. Historical FarmShare backend logs have not been verified;
  the preregistered SC v2 control helps compare under the same current runtime.
- FlashInfer availability warnings remain in the original logs. Actual attention
  selected FlashAttention 2; `VLLM_USE_FLASHINFER_SAMPLER=0` was retained as
  preregistered. No warnings were suppressed and no backend/dependency changes
  were made in response to these messages.

## Submitted follow-up jobs

| Job | Work | Last observed state |
|---|---|---|
| 18564747 | 27B v3 fixtures, seeds 329/330/331 | RUNNING |
| 18564765 | 27B v2-SC Main 1, seed 329 | RUNNING |
| 18564863 | 9B v3 fixtures, seeds 329/330/331 | PENDING (Priority) |
| 18564864 | 27B v3 Main 1, seeds 329/330/331 | PENDING (afterok:18564747) |
| 18564865 | 9B v3 Main 1, seeds 329/330/331 | PENDING (afterok:18564863) |
| 18564874 | v3 and v2-SC reports, no model calls | PENDING (afterok:18564864:18564865:18564765) |

Main 1 jobs have three/four-hour limits and wait for their respective fixture
jobs to exit successfully. The report job uses one CPU/4 GB and waits for both
v3 Main 1 jobs and the v2-SC control. It explicitly audits all seven Main 1 runs
and requires 60 terminal outcomes per run before writing any report. Thus a
partial run that exits zero at its time limit cannot silently yield a final
report. Recorded invalid outputs remain failures and do not block reporting
once every item has a terminal outcome. Report outputs are new files:
`outputs/rq1-v3/report.{json,md}` and `outputs/rq1-v2-sc/report.{json,md}`.

If a job is preempted or times out, inspect sacct and journal timestamps before
resuming identical inputs. Never retry recorded failures. No result commit or
push has been authorized yet; the prior approval covered the preregistration
commit only. Main 1 results and Main 2 sampling/annotation remain pending.
