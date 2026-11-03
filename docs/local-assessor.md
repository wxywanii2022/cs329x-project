# RQ1 local assessor (open-weight model, served on FarmShare)

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

## Next steps

1. **Confirm v2 on the development set** once the pilot items exist as raw prefixes.
2. **Pilot development set:** rebuild the 20 pilot items as raw prefixes from the source records (as `scripts/import_main60.py` does for Main 1); the existing pilot files are paraphrases with v0.1 labels.
3. **Participant linkage** for a true participant-disjoint test.

## Limitations

- **Order of development and test.** The 20 pilot items are the intended development set, but they exist only as paraphrased contexts with original v0.1 labels, not as the raw prefixes this pipeline uses. Main 1 was therefore run first with the settings above fixed in advance. Any change made after a later pilot run is a new, separately reported version; Main 1 results from these settings are not replaced.
- **Session-held-out, not participant-disjoint.** Main 1 has no `participant_id`; `--split test` cannot run until participant linkage is recovered.
- **Small reference.** 60 items with 4 zeros and 1 one: each false "0" moves the false-missed rate by ~1.8 points; read the bootstrap intervals, not point estimates.
- **Reproducibility.** Seeded sampling under concurrent batching is not bit-for-bit reproducible; the journals are the record of what the model produced. FP8 quantization is the vendor's official checkpoint, not BF16.
