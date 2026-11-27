# RQ2 main experiment: preregistration draft

**Status: draft (2026-11-23). Not frozen.** Freeze only after the gates in section 6
pass. To freeze: write `outputs/rq2-main/preregistration.json` with the SHA-256 of
every file listed in section 1 (the same way `outputs/rq1-v3/preregistration.json` was
written), before any call on a test-split task. No held-out (`split: "test"`) task may
be run, inspected in a model run, or used to tune anything before then.

## 1. What is frozen

- Config `configs/rq2-main/main.draft.json` (renamed `main.json` at freeze): seed 329,
  research mode, the same pinned models and decoding as the pilot.
- Roles: assessor = frozen v2 Qwen3.8-27B-FP8 (RQ1 Main 2); learner = Gemma 4 31B
  (`learner_v2`); coach = Ministral 3 14B (`coach_v2`); evaluator = gpt-oss-20b.
- Task assistant `scripted-table-v2`; learner view v2 (goal only); exercise bank
  `exercises.json`; profiles `profiles.json`; codebook v0.2 with contract
  `decision-point-v2`.
- All of `src/adaptive_tutor/**` (the runner records implementation hashes in each run's
  `frozen_inputs.json`), `scripts/rq2_pilot.sbatch`, `scripts/rq2_pooled_analysis.py`.

## 2. Design

6 profiles (novice, intermediate, expert; two variants each) × 8 held-out task pairs ×
AB/BA × 2 replicates = **192 run blocks** (768 branches).

- Primary set: `heldout_01`–`heldout_06`, incorrect-growth pairs, 144 blocks. Two pairs
  for each error type: change divided by the later value (wrong base), the count
  difference reported as a percentage, and an arithmetic slip. Forms within a pair share
  the error type and opportunities and differ in topic and values.
- Calibration set: `accurate_h1`, `accurate_h2`, accurate drafts (B4 has no
  opportunity), 48 blocks. These measure false alarms and unnecessary coaching, and keep
  every task from containing an error.

Each block runs one pre-task, assesses it, forks four branches (full,
without_assessment, without_background, no_coaching) from the same snapshot, delivers
at most one bank exercise (or none), and runs the matched post-task.

## 3. Outcomes and contrasts

Outcome per task: percentage of available rubric points from the evaluator's labels
(100 × sum of labels / (2 × scorable behaviors); N/A stays missing). Every contrast is a
within-block difference of post-task percentages. This equals the difference in gains,
because all four branches share one pre-task.

- **Primary:** full − no_coaching, within each reporting group, on the primary set.
  We report the estimate and its 95% interval. A coaching effect is claimed for a group
  only if the interval's lower bound is above 0.
- **Secondary contrasts:** without_assessment − no_coaching and without_background −
  no_coaching; full − without_assessment (the value of the explicit assessment) and
  full − without_background (the value of background). We also report per-behavior
  label differences, and repeat the primary contrast restricted to blocks with the same
  scorable behaviors in every compared record (sensitivity to denominator changes).
- **Secondary measures, each with its denominator:**
  - no-intervention rate, overall and in blocks where the assessor found no gap;
  - unnecessary coaching on the calibration set;
  - targeted-error rate (the final artifact's figure is wrong);
  - coaching turns and declines;
  - task-assistant help count;
  - failures by condition;
  - the natural chain from a spontaneous check to a correction;
  - coaching acceptability, rated by blinded humans on a subset (section 7).

Pre-task scores are reported per group to show baseline and ceiling.

## 4. Analysis

`python3 scripts/rq2_pooled_analysis.py outputs/rq2-main --pairs heldout_01 heldout_02
heldout_03 heldout_04 heldout_05 heldout_06` (the calibration set is analyzed
separately).

Uncertainty is a two-stage percentile bootstrap: resample task pairs, then blocks within
each pair, keeping every block's four branches together. It uses 10,000 resamples and
seed 329. Six pairs give limited task-level evidence, so intervals will be wide.
Repeated model samples estimate stochastic variability, not a human population. Turns,
rubric items and sibling branches are never treated as independent learners.

## 5. Failure handling

- **Transport failures:** retried up to 3 times (budget `transport_attempts`). Model
  outputs are never resampled for content, the same rule as RQ1.
- **Failed or unscored branches:** stay missing. Each contrast uses the blocks where
  both compared branches are complete, and missing branches are reported by condition.
  Difficult blocks are never dropped silently, and failures are never counted as
  learner mistakes.
- **Interruptions:** a run stopped by the time limit resumes from its journal with the
  same command. A changed input stops the run, and it then needs a new output directory.

## 6. Gates before freezing

The thresholds below are decision rules declared now, before the evidence exists. They
are not validated standards. If a gate fails, the component is revised on development
tasks, the pilot is rerun into a new directory, and the gate is checked again.

| Gate | Evidence | Pass rule |
| --- | --- | --- |
| Software | `audit` passes on every pilot 2 shard; branch and information isolation; resume tested | all pass |
| Fixtures | v2 assessor and evaluator on the 13 v0.2 fixtures and the 5 learner-view-v2 fixtures | reported; B2 shows 0, 1 and 2 on the new format, or the task view is revisited |
| Profile fidelity (humans) | two people independently read 4 uncoached pilot 2 pre-tasks per profile (24) and answer the guide's three questions: errors match the knowledge gaps; competent behavior stays possible; replies are not unrealistically compliant or formulaic | a transcript passes if both readers say yes to all three; a profile passes with at least 3 of 4 |
| Evaluator calibration (humans) | two people independently label 80 pilot 2 decision points (20 per behavior, stratified across groups, conditions, phases and forms) under v0.2 from blinded packets, then adjudicate | evaluator vs adjudicated κ ≥ 0.60 overall, no behavior below 0.40, false-missed rate ≤ 10%; human–human κ reported |
| Adaptation sanity | (a) pilot 2 coach decisions; (b) no-gap replay: `REPLAY_ARGS=--no-gap sbatch scripts/rq2_coach_replay.sbatch outputs/rq2-pilot-2 outputs/rq2-coach-nogap` re-sends the 48 full-condition coach requests with every assessor 0/1 rewritten to 2 (messages, prompt, model and seed unchanged) | (a) in the full condition at least 60% of exercises target an assessor 0/1; (b) the full coach chooses "none" in at least half of the blocks where the without_assessment coach also chose "none" on the same messages; the rate over all 48 is reported |

Gate (b) replaced "none is chosen at least once where the assessor saw no gap" on 2026-11-27, before the replay was run: in pilot 2 the assessor found a gap in all 48 blocks, so that case never occurred. The prompt tells the coach to check the assessment against the messages, so where the messages still show a gap an exercise is a defensible choice; the subset where the without_assessment coach saw no gap from the messages alone is the one where both signals agree.

For comparison, the assessor reached κ 0.87 and 2/52 false-missed on RQ1 Main 2.

## 7. Audits after the run

- **Second evaluator:** rescore a stratified 20% of records with a second evaluator
  from a fifth model family that fits one GPU. Proposed: Microsoft Phi-4-reasoning-plus.
  It still needs approval before download. Report label agreement and whether the sign
  of the primary contrast changes.
- **Coaching acceptability:** two blinded people rate a stratified subset of coaching
  decisions (context plus intervention; model, condition and outcome hidden). Learner
  acceptance alone is not evidence of quality.
- **Case analysis (proposal Part B):** compare successful and unsuccessful blocks for
  assessment errors behind coaching choices, mismatched support, persistent
  misconceptions and ceiling effects.

## 8. Compute

At pilot 1's pace the 192 blocks take about 9–10 hours on one 4×L40S node, limited by
the assessor. Run `RUNS=outputs/rq2-main sbatch --time=16:00:00 scripts/rq2_pilot.sbatch
configs/rq2-main/main.json`. The partition limit is 2 days, and resume covers
interruptions.
