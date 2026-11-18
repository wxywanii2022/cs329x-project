# RQ1 local assessor (FarmShare v1/v2; SC v3)

The `tutor-assess` pipeline ([assessment.md](assessment.md)) now has a real model behind it: an open-weight model served locally with vLLM and called through the `command` adapter `adaptive_tutor.adapters.local_vllm`. No API service is involved and the model sees only what the pipeline already allows: the frozen v0.2 rubric and the dialogue prefix up to the judged user turn.

## Models

| Role | Model (pinned revision) | Hardware | Why |
|---|---|---|---|
| Primary | `Qwen/Qwen3.8-27B-FP8@017b9c7af6b5689d5dd426a76e0bc077eb5ca20a` (dense 27.8B, Apache-2.0, Aug 2026) | 1× L40S 48 GB | Strongest open model that fits one card; 256k native context; thinking mode |
| Pre-declared size ablation | `Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a` (dense 9.7B, Apache-2.0, Feb 2026) | 1× L40S | ~10B class; reported regardless of its result |

What drove the choice (measured with the Qwen3.8 tokenizer on `data/rq1/main60`):

- Input size: the v0.2 rubric plus output contract is 3.1k tokens; total input has median 4.1k and 59/60 items are under 15k, but **M1-009 is 52k tokens**. A 32k-context model would record M1-009 as a failure, so the server runs with `--max-model-len 131072` (input + up to 32k output).
- The hard judgment is opportunity (N/A vs 0 vs scored): 42/60 adjudicated labels are N/A, only 4 are 0, and 9 of the 13 A/B disagreements are N/A vs a numeric label. Instruction following over a 28-section rubric matters more than speed. Vendor-reported IFBench: Qwen3.8-27B 79.5 vs Qwen3.5-9B 64.5 (not independently verified).
- Fit: FP8 weights are ~31 GB; only 16 of 64 layers keep a KV cache (the rest are linear attention), so a 131k context costs ~8 GB and fits one card.

## Pre-declared protocol (fixed before any Main 1 call)

- Runtime: vLLM 0.32.0, torch 2.13 / CUDA 13.0, `--reasoning-parser qwen3 --language-model-only`, weights loaded offline from the pinned revisions.
- Prompt: unchanged pipeline request (frozen v0.2 rubric + output contract as system message, canonical JSON payload as user message), same construction as `http_bridge`.
- Decoding: thinking on; each model's published thinking-mode settings: temperature 1.0, top_p 0.95, top_k 20, min_p 0, presence penalty 0 (Qwen3.8) or 1.5 (Qwen3.5, "general tasks"). Qwen advises against greedy decoding in thinking mode. Per-request seed from the pipeline's `sample_seed`.
- Output: the final answer (after thinking) is constrained by a JSON schema that encodes the contract's three consistent label/status/na_reason shapes and restricts evidence `turn_id` to visible IDs. The pipeline's validator still decides; exact-quote checks are not enforced by decoding. Invalid or truncated outputs are recorded failures, never repaired or resampled.
- Budget: `max_output_tokens` 32768 (thinking tokens count as output), `max_context_bytes` 200000 (unchanged), 3 transport attempts (connection errors only).
- Runs: seeds 329 (**primary**), 330, 331 for each model, run concurrently against one server.
- Analysis (`scripts/rq1_report.py`): agreement with adjudicated, A and B separately; raw agreement, unweighted κ, false-missed rate (model 0 among reference 1/2/N/A); 95% percentile bootstrap over items; failures reported separately, never counted as N/A. Secondary: per-behavior tables (≈15 items each, descriptive), A/B-agreed vs A/B-disagreed subsets, seed stability, and majority-of-seeds labels (ties go to the primary seed).

Thinking traces are kept out of the pipeline envelope but appended to `trace.jsonl` in each run directory for error analysis. They can quote evidence, so they stay in the ignored `outputs/` tree like the journals.

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install "vllm==0.32.0" huggingface_hub && .venv/bin/pip install -e .
.venv/bin/python -c "from huggingface_hub import snapshot_download as d; \
  d('Qwen/Qwen3.8-27B-FP8', revision='017b9c7af6b5689d5dd426a76e0bc077eb5ca20a'); \
  d('Qwen/Qwen3.5-9B', revision='c202236235762e1c871ad0ccb60c8ee5ba337b9a')"

# Operational check: 4 synthetic items + one 53k-token synthetic item (no human labels)
sbatch -t 00:45:00 scripts/rq1_vllm.sbatch configs/assessment.qwen38-27b-fp8.json smoke
# Main 1: three seeds, then evaluate vs A, B and adjudicated
sbatch -t 03:00:00 scripts/rq1_vllm.sbatch configs/assessment.qwen38-27b-fp8.json main60
sbatch -t 04:00:00 -c 4 --mem=15600M scripts/rq1_vllm.sbatch configs/assessment.qwen35-9b.json main60
.venv/bin/python scripts/rq1_report.py --runs outputs/rq1 --data data/rq1/main60 --save outputs/rq1/report
```

On FarmShare, GPUs are often free while CPUs on those nodes are not, and memory is capped at 4000 MB per CPU, so the script asks for 6 CPUs / 23.4 GB (the 27B server peaks near 17 GB host RSS while loading; the 9B fits in 4 CPUs / 15.6 GB). Short time limits also backfill sooner. Rerunning the same command resumes a run (`--export=ALL,SEEDS=330` resumes one seed); changing the config, code or items requires a new output directory (the pipeline enforces this). A run killed outside the script's time-limit handler (e.g. `scancel`) leaves its `.run.lock`; delete it once `sacct` shows the job ended.

Smoke-test timing on one L40S: Qwen3.8-27B 12–41 s per item (about 300–600 output tokens including thinking; 41 s for the 53k-token item); Qwen3.5-9B 42–88 s (thinks 4–6× longer). The job script sets `VLLM_USE_FLASHINFER_SAMPLER=0` because FlashInfer's fused sampler needs `nvcc`, which the GPU nodes lack; vLLM does not use that sampler for seeded requests, so the sampling path is unchanged.

## SC execution for v3

The v1/v2 FarmShare script is preserved. `scripts/rq1_vllm_sc.sbatch` uses SC account
`nlp`, partition `jag-standard`, one `rtx6000ada`, 8 CPUs and 48 GB host memory.
All v3 runs used RTX 6000 Ada; the historical v1/v2 runs used L40S. The pinned
models, vLLM arguments, decoding and seeds were unchanged. The preregistered
same-hardware control reran v2's primary 27B seed on SC in `outputs/rq1-v2-sc`,
never in the historical result directories. Preregistration was pushed as
`d6e17c1` before the first v3 call.

- Code and `.venv`: `/nlp/scr/yuantian/cs329x-project`; HF cache:
  `/nlp/scr/yuantian/hf`. The observed user filesystem capacity is **200 GB**, not
  the capacity of the underlying storage pool. The script explicitly puts HF,
  application caches and temporary files on scratch; no `.bashrc` change is needed.
- Follow the [SC wiki](https://cluster.cs.stanford.edu/sc/): transfer code, wheels
  and pinned model snapshots on `scdt`; build/install the runtime and test CUDA
  inside a Slurm allocation. No heavy tasks on `sc`. Download binary wheels with
  `pip download --only-binary=:all:` on `scdt`, then install offline on the worker.
  Save the resolved package versions and GPU/driver information with setup logs.
- **Before any v3 inference, including smoke**, choose the primary rule and commit
  and push `outputs/rq1-v3/preregistration.json`. The script checks its presence;
  the operator must additionally verify its contents and that it was pushed. This
  takes precedence over a workflow that places smoke before preregistration.
- Create `outputs/logs` before `sbatch` (Slurm opens its output before the script).
  The SC script defaults to `RUNS=outputs/rq1-v3` and refuses the historical v1/v2
  output trees. Existing seed configs and synthetic smoke inputs must match exactly;
  each execution/resume keeps a distinct stdout/server log. Failed annotations are
  never repaired or resampled. The pipeline continues to enforce frozen-input hashes.
- `fixtures` evaluates 13 constructed cases with `synthetic-fixture` provenance;
  this is an operational/rule-application check, not an accuracy estimate.
- `jag-standard` can preempt/requeue jobs. Match `sacct` state and job restart count
  against journal timestamps; document interruptions rather than rewriting failures.
  Remove a stale lock only after confirming the owning job is finished. Automatic
  requeue does not authorize deleting a lock or retrying a recorded failure.

After the preregistration is pushed and setup/weights are verified:

```bash
mkdir -p outputs/logs
sbatch -t 00:45:00 scripts/rq1_vllm_sc.sbatch configs/v3/assessment.qwen38-27b-fp8.json smoke
sbatch -t 01:00:00 scripts/rq1_vllm_sc.sbatch configs/v3/assessment.qwen38-27b-fp8.json fixtures
sbatch -t 01:00:00 scripts/rq1_vllm_sc.sbatch configs/v3/assessment.qwen35-9b.json fixtures
sbatch -t 03:00:00 scripts/rq1_vllm_sc.sbatch configs/v3/assessment.qwen38-27b-fp8.json main60
sbatch -t 04:00:00 scripts/rq1_vllm_sc.sbatch configs/v3/assessment.qwen35-9b.json main60
# Same-hardware control, included in the approved preregistration.
sbatch -t 02:00:00 --export=ALL,RUNS=outputs/rq1-v2-sc,SEEDS=329 scripts/rq1_vllm_sc.sbatch configs/v2/assessment.qwen38-27b-fp8.json main60
```

The default is seeds 329/330/331 for fixtures and Main 1; smoke uses only 329.
Run the smoke command with the 9B v3 config as well before its fixture/Main 1 runs.

**Primary decision (Yuan Tian): option (a), Qwen3.8-27B-FP8 seed 329.** Seeds 330/331,
three-seed majority voting (only items valid in all three; ties use 329), and the
high-confidence-zero rule on valid seed-329 outputs are secondary, never replacements
for the primary result. The latter is a derived analysis, not a change to raw labels;
failed outputs stay failed. The 9B results are reported regardless of performance.

`rq1_report.py` reports explicit FMR counts and coverage, follows the six v2 false-missed
items, and excludes all v3 failures from every scoring analysis. The historical
quote-failure sensitivity remains available only for v1/v2: v3's opportunity check
follows quote validation, so a quote failure cannot be assumed otherwise valid.
For v3, all three seeds must finish (including recorded failures) before generating
the report. Existing report files are never overwritten; choose a new `--save` prefix.

The SC script's mock orchestration tests cover smoke/resume, immutable seed configs,
all fixture seeds, three-reference evaluation and protection of historical outputs.
These offline tests are not evidence of real-model readiness or v3 accuracy.

## Results (Main 1, run 2026-11-02)

Full tables, confusion matrices, per-seed failures and the disagreement list with model reasons: `outputs/rq1/report.md` (regenerate with `scripts/rq1_report.py`). Agreement is over successfully labeled items; 95% bootstrap intervals over items.

| Comparison | n | Raw agreement | Cohen's κ | False-missed rate |
|---|---|---|---|---|
| Human A vs B (pre-adjudication) | 59 | 0.780 [0.68, 0.88] | 0.590 [0.40, 0.76] | 0.056 [0.00, 0.12] |
| Human A vs adjudicated | 60 | 0.933 [0.87, 0.98] | 0.863 [0.72, 0.97] | 0.036 [0.00, 0.09] |
| Human B vs adjudicated | 59 | 0.847 [0.75, 0.93] | 0.702 [0.53, 0.86] | 0.036 [0.00, 0.09] |
| **Qwen3.8-27B, primary (seed 329) vs adjudicated** | **44** | **0.864 [0.75, 0.95]** | **0.720 [0.50, 0.90]** | **0.075 [0.00, 0.17]** (3/40) |
| Qwen3.8-27B primary vs A / vs B | 44 / 43 | 0.909 / 0.791 | 0.826 / 0.599 | 0.051 / 0.079 |
| Qwen3.8-27B seed 330 vs adjudicated | 46 | 0.891 | 0.772 | 0.047 |
| Qwen3.8-27B seed 331 vs adjudicated | 45 | 0.844 | 0.674 | 0.095 |
| Qwen3.5-9B, primary (seed 329) vs adjudicated | 34 | 0.824 [0.68, 0.94] | 0.570 [0.24, 0.83] | 0.062 [0.00, 0.16] |

Coverage is the main weakness. Under the strict contract, 16/60 primary 27B outputs (14 and 15 in seeds 330 and 331) and 26/60 primary 9B outputs are recorded failures. Every 27B failure except seed 330's infrastructure abort (incident 4), and all but one 9B failure, is the exact-quote check; the remaining 9B failure is a runaway thinking trace that hit the 32k cap. No failure is counted as N/A.

- **Why quotes fail.** Every failed 27B item has exactly one bad quote, and the 27B copies the right text: of its 44 failing quotes across seeds, 40 differ from the source only in line breaks (newline written as a space, dropped, or as `⏎`/U+2028), 3 swap straight quote marks for curly ones, and 1 shortens the text with `...`. Of the 9B's 87, 30 are line-break-only, 27 shortened with `...`, 5 quote-mark swaps and 25 reworded (capitalization changes, or a summary instead of a quote). Both errors sit where the JSON-encoded input has escapes (`\n`, `\"`). In the primary run, 14 of the 16 quote-failed 27B items carry the adjudicated label anyway; the other two (M1-034, M1-060) say 0 where the reference is N/A.
- **Post-hoc check (not pre-declared).** Scoring the outputs that failed only the quote check gives the 27B primary run 60 items, raw 0.867 [0.78, 0.95], κ 0.749 [0.58, 0.90], false-missed 0.089 [0.02, 0.17]; the 9B gives 59 items, κ 0.603. The quote failures do not hide worse labels, but this is a sensitivity analysis, not the headline result.
- **Where the 27B disagrees.** 31/32 correct on items where A and B agreed, 6/11 where they disagreed. Five of its six disagreements are human-disputed items where it sided with the annotator the adjudication overruled (M1-005, M1-016, M1-026, M1-030, M1-044); one is a clear error (M1-046, B3: all humans N/A, model 0).
- **False-missed cases** (primary): M1-005, M1-044, M1-046, all B3, all adjudicated N/A. In the first two, annotator A also said 0. Descriptive per-behavior agreement: B1 10/11, B2 9/10, B3 8/12, B4 11/11. B3 (accept-and-move-on vs. no substantive claim) is the weakest boundary.
- **27B vs 9B.** The 27B has higher point estimates, better coverage (44 vs 34), shorter thinking (median 1.2k vs 3.7k output tokens) and is faster (median 55 s vs 97 s per item), but the intervals overlap heavily; n is too small to claim a significant difference.
- **Seed stability** (items labeled in all three seeds): 27B 30/36 unanimous, mean pairwise κ 0.79 (unstable: M1-005, M1-026, M1-027, M1-031, M1-046, M1-055); 9B 16/22, κ 0.59. Majority-of-seeds labels (secondary) do not beat the primary seed: 27B κ 0.705 vs adjudicated.

Reading: on the items it labels, the 27B agrees with the adjudicated reference about as well as an individual annotator does (B: κ 0.70) and better than the two annotators agree with each other (0.59), and its errors concentrate on cases humans also found ambiguous. It is **not yet a validated assessor**: about a quarter of its outputs fail the evidence contract, so coverage must be fixed in a new protocol version before it can label RQ2 data unattended.

## Incidents and deviations

Recorded so the run can be audited; none changed a recorded model output.

1. **Before Main 1:** the job script sets `VLLM_USE_FLASHINFER_SAMPLER=0` (see above).
2. **Post-hoc analysis:** the quote-only sensitivity rows were added to `rq1_report.py` after the 9B failures were seen. `outputs/rq1/preregistration.json` holds the pre-run hashes of the protocol, configs and scripts.
3. **Journal reader bug:** the primary 27B journal contains model text with U+2028, which `canonical()` writes unescaped and `str.splitlines()` (used by `Journal.read` and `load_items`) treats as a line break, so the journal looked "damaged". All six journals' hash chains verify when split on `\n`. `storage.py` and `pipeline.py` now split on `\n` only (regression test added); results above use the fixed reader.
4. **27B seed 330** hit its time limit at 51/60. SLURM signalled vLLM and the pipeline together, so one in-flight request came back `finish_reason: abort` and is journaled as a failure (infrastructure, not model behavior). The job script now stops the pipeline runs before the server (`--signal=B:USR1@180`), and the adapter treats `abort` as a retryable transport error. Because package code changed after the run started, the resume job runs against a byte-identical snapshot of the original code (`outputs/rq1/code-snapshot/src`, implementation hashes verified equal) so the pipeline's frozen-input check still holds. The resume (job 1924873) completed the remaining 9 items (M1-052–M1-060), all labeled.
5. **Job script `wait` bug:** the first resume attempt made no progress. The killed run had left its `.run.lock` (SIGTERM skips the pipeline's lock cleanup), and the job then idled to its limit because a bare `wait` also waited on the vLLM server. The same bug made the 9B Main 1 job idle from 04:13, when all three seeds had finished, to its 04:22 limit without running `evaluate` (done afterwards on the login node); the 27B job ran out of time mid-run (incident 4). The script now waits on the pipeline runs only, and its time-limit handler releases locks held by the runs it stopped, never anyone else's.
6. **v2 job limits:** the v2 27B jobs (one seed each, 1h10 limit so they start sooner) stopped at the limit with 39, 40 and 47 items done. The graceful stop recorded no failure, and resume jobs 1926354–1926356 finished the rest. The first seed-329 job ended as TIMEOUT rather than COMPLETED because vLLM's shutdown waited on the stopped client's open request; nothing was journaled after the stop.

7. **SC execution (v3 and same-hardware v2 control):** historical v1/v2 used FarmShare L40S; v3 used SC RTX 6000 Ada. Runtime was vLLM 0.32.0, torch 2.13.0+cu130 and driver 610.43.02; exact packages and `sacct` records are retained under `outputs/rq1-v3/runtime/`. vLLM selected Marlin weight-only FP8 for the 27B block-scaled checkpoint and FlashAttention 2. FlashInfer availability warnings remain in the logs; backend/sampling settings were not changed or warnings suppressed. Hardware FP8 capability alone does not describe the selected arithmetic path. All new jobs completed with zero restarts and no journaled transport failures.
8. **v3 byte-budget boundary:** the extra contract text makes M1-009 exceed the unchanged 200,000-byte request budget by 593 bytes (27B primary), despite successful synthetic long-context smoke. All six v3 outcomes for M1-009 remain failed. This was identified after the completed runs, not repaired or rerun; see the v3 results and supplemental audit below.

## Protocol v2: quote rule and quoting instruction (2026-11-02)

v1 lost about a quarter of its items to formatting differences in quotes, which the assessor owner (cren8) judged not to be errors. v2 changes only how evidence is quoted and checked; the v0.2 labeling rules, models, decoding, seeds, budgets and analysis are unchanged. **The change was designed after seeing v1's Main 1 failures**, so v2 on Main 1 is not a held-out test of the change itself. It is reported next to v1, never instead of it, and the pilot development set should confirm it. Settings are fixed in `configs/v2/` and hashed in `outputs/rq1-v2/preregistration.json` before any v2 call.

1. **Quote check** (`quote_found` in `rq1/core.py`, contract `decision-point-v2`). Exact substrings still pass. Otherwise only letters and digits are compared (NFKC, case-folded), so line breaks, spacing, punctuation, quote-mark style, markdown and case do not matter. Omissions are allowed when marked `...` or between verbatim runs of at least 20 letters (about four words), and every piece must appear in the cited turn, in order. Changed, invented or reordered words still fail.
2. **Prompt:** one paragraph appended to the output contract: copy quotes verbatim, never paraphrase or describe; prefer short excerpts; cite separate parts as separate entries; mark omissions with `...`; line breaks may be written as spaces.
3. **Replay check of the rule on v1 outputs** (a check of the rule, not a v2 result). No output that v1 accepted is rejected. All 44 of the 27B's quote failures pass. 74 of the 9B's 83 quote-failed items pass; the other 9 contain invented words, reordered text, or (once) a wrong final character.

Run: `configs/v2/*.json` with `RUNS=outputs/rq1-v2`, e.g. `sbatch -t 01:10:00 --export=ALL,RUNS=outputs/rq1-v2,SEEDS=329 scripts/rq1_vllm.sbatch configs/v2/assessment.qwen38-27b-fp8.json main60` (rerun the same command to resume), then `scripts/rq1_report.py --runs outputs/rq1-v2 --save outputs/rq1-v2/report`.

### v2 results (Main 1, run 2026-11-02)

Full tables: `outputs/rq1-v2/report.md`. Same reference, metrics and intervals as the v1 results above.

| Comparison | n | Raw agreement | Cohen's κ | False-missed rate |
|---|---|---|---|---|
| **Qwen3.8-27B, primary (seed 329) vs adjudicated** | **60** | **0.833 [0.73, 0.92]** | **0.688 [0.50, 0.85]** | **0.107 [0.04, 0.19]** (6/56) |
| Qwen3.8-27B primary vs A / vs B | 60 / 59 | 0.900 / 0.780 | 0.820 / 0.618 | 0.073 / 0.130 |
| Qwen3.8-27B seed 330 vs adjudicated | 60 | 0.850 | 0.708 | 0.054 |
| Qwen3.8-27B seed 331 vs adjudicated | 60 | 0.850 | 0.712 | 0.071 |
| Qwen3.5-9B, primary (seed 329) vs adjudicated | 59 | 0.814 [0.71, 0.90] | 0.580 [0.35, 0.77] | 0.073 [0.02, 0.15] |
| Qwen3.5-9B seeds 330 / 331 vs adjudicated | 57 / 59 | 0.860 / 0.847 | 0.702 / 0.671 | 0.038 / 0.036 |

- **Coverage.** The 27B labeled all 180 calls (3 seeds × 60) with no failure. The 9B labeled 175/180, down from 84 failures in v1 to 5:
  - **Runaway thinking (1):** M1-013, seed 330, used all 32,768 output tokens without an answer.
  - **Changed words (2):** M1-040 (seed 330) rewrote `the [FILE_2].md file is currently in` as a guessed file name and "is saved in"; M1-013 (seed 331) wrote `Material Spe...` for `Material [FILE_1].docx`.
  - **Wrong turn (1):** M1-042 (seed 330) quoted turn 8 verbatim but cited turn 25.
  - **`&` written as "and" (1):** M1-006 (seed 329), turn 12; a later turn has the "and" wording verbatim.

  The rule was not changed after these were seen.
- **Same items, v1 vs v2.** v2 changes coverage, not labeling quality.
  - On the items v1 had labeled, v2 differs from v1's same-seed 27B label on 12/135 (8.9%). Two seeds of one version differ about as often (11%).
  - Pooled over seeds, v1 is right and v2 wrong on 8 of these items, and the reverse on 3. Per seed, v2 is 1–2 items lower (primary: 36/44 vs 38/44). This is within resampling noise.
  - On the 16 items v1 lost, the v2 primary run matches the adjudicated label on 14.
  - The headline moves from v1's κ 0.720 / false-missed 0.075 (on 44 items) to 0.688 / 0.107 (on all 60).
- **Where the 27B disagrees** (primary, 10 items). It matches 44/46 items where A and B agreed and 5/13 where they disagreed.
  - In six disagreements it gives the label of the annotator the adjudication overruled (M1-005, M1-016, M1-030, M1-031, M1-044, M1-055).
  - In two it gives a third label on a disputed item (M1-034, M1-040).
  - Two are clear errors (M1-027, M1-035: both annotators N/A, model 0).
- **False-missed is the main remaining weakness:** 6/56, three times the annotators' 0.036 vs adjudicated, though the intervals overlap.
  - Every case is a 0 where the reference is N/A: M1-005, M1-027, M1-034, M1-035, M1-040, M1-044.
  - Four are items where one annotator also gave a non-N/A label.
  - Per behavior: B2 3, B3 2, B4 1, B1 0.
- **Seed stability:** 27B 50/60 items unanimous, mean pairwise κ 0.81; majority-of-seeds κ 0.713, false-missed 0.089 (secondary). 9B: 45/56, κ 0.70.
- **27B vs 9B:** with near-full 9B coverage the gap narrows. The 27B leads on the primary seed (κ 0.688 vs 0.580), but the 9B's other seeds are comparable and its false-missed rate is lower; the intervals overlap, so no difference is claimed. The 27B thinks less and runs faster: median 1.4–1.6k output tokens and 57–65 s per item, vs 1.4–3.6k tokens and 38–92 s for the 9B.

Reading: under v2 the 27B labels every Main 1 item with checked evidence. Its agreement with the adjudicated reference (κ 0.69) is close to a single annotator's (B: 0.70) and above A–B agreement (0.59). Its false-missed rate is higher than the annotators', mostly 0-for-N/A calls on items the humans disputed. It is still **not a validated assessor**: v2 was fixed after seeing Main 1, so the pilot development set must confirm it before it labels RQ2 data.

## Protocol v3: opportunity gate (designed 2026-11-14; run 2026-11-17–18)

Goal: cut false "missed" labels without changing the v0.2 rules. All six v2 false-missed errors are 0 where the reference is N/A, and in each the model's reason describes only what the user did not do, never whether the opportunity existed. v3 targets that step. **v3 was designed after reading these six errors**, so v3 on Main 1 is a development result, reported next to v2 and never instead of it; only a new, independently labeled batch can test it.

1. **Frozen rules unchanged.** The v0.2 rubric file and its hash check are untouched; v3 is a new output contract (`decision-point-v3` in `rq1/core.py`) that appends to v2. The quote rule is v2's.
2. **Prompt: opportunity gate.** Before any 0 the model must walk the v0.2 N/A conditions for the assigned behavior (restated from sections 5, 8–20 with section references) and return N/A if any holds or it cannot tell. The B2 list makes explicit that troubleshooting, file handling, formatting and design requests are not evidence-dependent outputs; the B3 list that a preceding file location, progress update or plan is not a checkable claim; the B4 list that a new preference is B1.
3. **Validator: a 0 must cite its opportunity.** Under v3, a B3 0 needs an evidence quote from an earlier assistant or tool turn (the claim the user did not check), and a B4 0 needs a quote from any turn before the target (the problem). Otherwise the output is a **failure**, not N/A, consistent with the existing failure policy, so coverage is reported alongside FMR. B1/B2 zeros cite the request itself and are not gated, because their opportunity lives in the target turn and the task instructions.
4. **Configs:** `configs/v3/` (same models, decoding, seeds and budgets as v2). Run with `RUNS=outputs/rq1-v3`, e.g. `sbatch --export=ALL,RUNS=outputs/rq1-v3,SEEDS=329 scripts/rq1_vllm.sbatch configs/v3/assessment.qwen38-27b-fp8.json main60`, then `scripts/rq1_report.py --runs outputs/rq1-v3 --save outputs/rq1-v3/report`.
5. **RQ2 stays on v2 for now** (`ASSESSMENT_CONTRACT` in `schema.py`). Switch it only after the held-out result below decides which contract is primary, and then for both assessor and evaluator.

### v3 results (Main 1, development)

**The primary run gives fewer false "missed" labels, but also flags fewer genuine
missed behaviors. This is a development result, not a held-out validation.** The
primary remains option (a), 27B seed 329; neither seed 330's stronger agreement nor
a secondary confidence rule replaces it.

All model/report jobs completed normally with exit 0 and zero Slurm restarts.
All 15 new run journals (smoke, fixtures, Main 1 and the SC v2 control) passed
hash-chain/evidence audits, had every planned item outcome, and recorded no
transport failure. A completed job does not imply every model output was valid.
Full tables: `outputs/rq1-v3/report.md`, `outputs/rq1-v2-sc/report.md`.
Supplemental audit/count comparison: `outputs/rq1-v3/completed-audit-and-comparison.json`.

| Run vs adjudicated | Coverage | Raw agreement | κ | FMR (count) |
|---|---|---|---|---|
| Historical v2 27B, seed 329 (L40S) | 60/60 | 0.833 | 0.688 | 0.107 (6/56) |
| v2 27B SC control, seed 329 | 60/60 | 0.817 | 0.652 | 0.089 (5/56) |
| **v3 27B, seed 329 (primary)** | **59/60** | **0.831** | **0.666** | **0.036 (2/55)** |
| v3 27B, seed 330 | 59/60 | 0.915 | 0.826 | 0.018 (1/55) |
| v3 27B, seed 331 | 59/60 | 0.831 | 0.669 | 0.073 (4/55) |
| v3 9B, seed 329 | 57/60 | 0.895 | 0.753 | 0.019 (1/54) |
| v3 9B, seed 330 | 56/60 | 0.911 | 0.789 | 0.038 (2/53) |
| v3 9B, seed 331 | 56/60 | 0.839 | 0.637 | 0.058 (3/52) |

Primary 27B 95% item-bootstrap intervals are κ [0.48, 0.83], raw agreement
[0.73, 0.92] and FMR [0.00, 0.09]; the SC v2 control gives κ [0.47, 0.81]
and FMR [0.02, 0.17]. These small, overlapping estimates do not establish an
improvement. The original v2 and SC v2 primary labels differ on 5/60 items;
this rerun does not isolate hardware from batching/randomness or dependency differences.

Against A and B separately, the v3 27B primary gives n=59/58, raw=0.864/0.793,
κ=0.745/0.626 and FMR=1/54 / 2/53. The 9B primary gives n=57/56,
raw=0.860/0.839, κ=0.695/0.669 and FMR=1/53 / 1/52. B's unfinished M1-053
remains missing, not N/A. Full intervals for each reference are in the reports.

**Coverage loss has an identified cause.** M1-009 fails the unchanged 200,000-byte
request budget in every v3 seed/model. For the 27B primary, the complete request
is 198,365 bytes under v2 and 200,593 under v3: the appended contract adds 2,228
bytes. This is not GPU OOM or a failed opportunity quote, and no model call was
made for that item. The successful 53k-token synthetic smoke case did not establish
that this different real request would fit the byte budget. No budget was raised,
no input truncated, and no recorded failure rerun or relabeled.

The 27B has no other Main 1 failures (177/180 valid outcomes). The 9B has
169/180 valid outcomes: three budget failures, six quote failures, one missing-field
output and one opportunity-evidence failure (M1-041, primary seed). Failures are
excluded from scoring and remain failures; no v3 quote-only sensitivity rescoring
is applied.

**Descriptive trade-off on common items.** On the 59 items valid under both SC
primary runs, v2 has FMR 5/55, raw 0.814 and κ 0.651; v3 has FMR 2/55, raw 0.831
and κ 0.666. Thus losing M1-009 does not by itself account for the lower false-missed
numerator. But of the four reference zeros, v2-SC flags 2/4 and v3 only 1/4
(historical v2: 3/4). These supplementary counts suggest a more conservative
missed-behavior detector, not an unqualified increase in reliability.

The six historical v2 false-missed items all have reference N/A:

| Item | v3 primary outcome | Interpretation |
|---|---|---|
| M1-005 | 0 | Still false missed |
| M1-027 | N/A | Matches reference |
| M1-034 | 1 | No longer false missed, but still disagrees |
| M1-035 | 0 | Still false missed |
| M1-040 | N/A | Matches reference |
| M1-044 | N/A | Matches reference |

**Secondary rules remain secondary.** 27B majority voting gives κ 0.700,
FMR 3/55 and coverage 59/60. The high-confidence-zero rule gives κ 0.721,
FMR 0/55 and coverage 59/60, still flagging only one of four reference zeros.
Zero observed errors (and its degenerate percentile-bootstrap interval) do not
establish zero risk. The 9B majority result is κ 0.863 and FMR 1/49, but on only
52/60 jointly valid items; its confidence rule does not change the primary labels.

**Fixtures are a rule-application check, not accuracy evidence.** The 27B produces
13/13 valid outputs per seed, matching the constructed reference on 11/13 each.
All seeds disagree on F01 and F04, both reference zeros. The 9B produces 12/13
valid per seed (one quote failure each), matching 10/12, 9/12 and 9/12 valid pairs.
These disagreements/failures are retained, not used to retune v3 or rewrite fixtures.

### Held-out test for v3 (to fix before any held-out call)

- **Development material only:** `data/rq2/v02_fixtures` (13 constructed items, add N/A-boundary cases in `scripts/build_v02_fixtures.py`) and the pilot items once rebuilt as raw prefixes. Do not tune on Main 1 (see `data/rq1/main60/README.md`).
- **Primary decision rule, chosen in advance** in `outputs/rq1-v3/preregistration.json`: one of (a) v3 primary seed, (b) v3 majority of three seeds, (c) v3 with a 0 kept only at high confidence (else N/A). Report the others as secondary.
- **New batch (Main 2):** from sessions used in neither pilot nor Main 1, preferring participants not seen before. Enrich opportunities with a rule written down before sampling and blind to labels, e.g. B3/B4 targets are not a session's first user turn and follow an assistant turn with figures or conclusions; B2 targets request an output. Draw randomly among eligible turns with fixed seeds. About 60–80 items, labeled independently by A and B under v0.2 and adjudicated as in Main 1.
- **Report** κ, FMR with numerator/denominator, and coverage for v2 and v3 on Main 2. Because Main 2 is enriched, do not pool its FMR with Main 1's.
- **If FMR does not drop**, keep the preregistered contract for RQ2 and report false "missed" labels, and the unneeded coaching they trigger, as a finding.

## Next steps

1. **Development runs completed; keep the frozen primary rule (a).** Review the coverage and false-/true-missed trade-off without retuning on Main 1.
2. **Label Main 2 independently**, then adjudicate and run the frozen v3 and v2. A 60-item session-held-out annotation pack has been prepared and uploaded with user approval; it is not fully participant-disjoint. Two selected items exceed the current byte budget, so resolve and preregister the execution-budget policy before any held-out model call, consistently for v2/v3. No Main 2 labels or model prelabels have been generated by the agent.
3. **Pilot development set:** rebuild the 20 pilot items as raw prefixes from the source records (as `scripts/import_main60.py` does for Main 1); the existing pilot files are paraphrases with v0.1 labels.
4. **Participant linkage** for a true participant-disjoint test.

## Limitations

- **Order of development and test.** The 20 pilot items are the intended development set, but they exist only as paraphrased contexts with original v0.1 labels, not as the raw prefixes this pipeline uses. Main 1 was therefore run first with the settings above fixed in advance. Any change made after a later pilot run is a new, separately reported version; Main 1 results from these settings are not replaced.
- **Session-held-out, not participant-disjoint.** Main 1 has no `participant_id`; `--split test` cannot run until participant linkage is recovered.
- **Small reference.** 60 items with 4 zeros and 1 one: each false "0" moves the false-missed rate by ~1.8 points; read the bootstrap intervals, not point estimates.
- **Reproducibility.** Seeded sampling under concurrent batching is not bit-for-bit reproducible; the journals are the record of what the model produced. FP8 quantization is the vendor's official checkpoint, not BF16.
