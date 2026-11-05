# Implementation decisions and research gates

## Source of truth

The proposal's opening section describes four branches with retained learner history. The supplied simulator guide makes that design concrete. Older proposal text later in the same DOCX describes a two-arm study with removed personal memory; that is historical material and is not the implemented protocol. Both original DOCX files are preserved unchanged.

The simulator implements immediate transfer with retained conversational context. It makes no claim about lasting human learning or updated model weights.

## One rubric for RQ1 and RQ2

RQ2 applies the frozen RQ1 codebook **v0.2** without changes, and the assessor and evaluator use the evaluated output contract **`decision-point-v2`** (quote checking) through the same payload builder and validator as RQ1. The codebook defines labels; the contract defines the output format and evidence checks. They are versioned separately.

An earlier candidate rubric, `sim-opportunities-v1`, kept the guide's tasks (requirements and a source table supplied to the learner) and changed the rules so B1/B2 still counted. Under v0.2 those tasks have no B1/B2 opportunity: supplied requirements make B1 N/A and supplied sources make B2 N/A. We changed the tasks instead of the rules. The learner now receives a goal ("tell a colleague how completed requests changed") and a description of the data the assistant holds, with no prescribed format and no values. The numeric table stays with the scripted task agent. Whether a given simulated dialogue contains an opportunity is still judged from the visible prefix, as in RQ1.

| Behavior | Decision point | What the task leaves open |
| --- | --- | --- |
| B1 | Initial learner request | Format, length, audience and content are not prescribed |
| B2 | Initial learner request | The learner has no sources; it can ask for the calculation or a citation |
| B3 | Learner response to the draft, before any disclosure | The draft's growth claim is wrong (35% for 28%) |
| B4 | Learner response to the fixed disclosure, or the review turn if the learner already named the error and asked for a fix | The error is visible and open to correction |

Shared code does not imply shared accuracy. Before research runs, run the assessor on the constructed cases in `data/rq2/v02_fixtures` (including the B2 boundary between naming the assistant's table, F04, and supplying the evidence rule or source values, F12/F13) and compare it with human labels on a sample of simulator records, with particular attention to the B1/B2 N/A-versus-0 boundary.

The fixture `accurate_01` still permits checking a specific claim but has no B4 problem. `no_trigger_01` supplies a preference task with no scored opportunities. `incomplete_01` deliberately has no captured dialogue, producing `insufficient_evidence` instead of zeros. These cases test observability and N/A handling; they are not primary transfer pairs.

## Controlled assistance and simulated adaptation

The task agent fixes the initial growth claim, calculates follow-up evidence deterministically, and preserves an incorrect draft unless a recognizable correction request occurs. If the learner names the error and asks for a fix at review, the agent applies it then; the fixed disclosure that follows reports that the revised draft agrees with the table, and B4 is scored at the review turn (`b4_decision_stage`). All branches still receive the same disclosure. Its request parsing is deliberately limited to visible lexical patterns, documented in `tasks.py`; it is not a general natural-language tutor.

The `discovery` field distinguishes spontaneous checking from prompted disclosure. `spontaneous_check_then_correction` reports that observable sequence. Correction before disclosure is possible but requires the learner to name the error without the table, so most B4 decisions still follow the standardized disclosure. B4 must not be described as an unprompted naturalistic correction rate. A separate naturalistic protocol would be needed to remove that disclosure.

Six candidate knowledge profiles cover three reporting groups with two variants each. Domain knowledge, response-length preference and time availability are matched. The initial date is fixed in the profile data. There is no skill counter, automatic gain, hidden memory update or instruction to achieve a target score. Real learner calls always use the same policy and their own observed history.

The mock learner samples canned responses without reference to reporting group or treatment. The mock assessor and evaluator use lexical rules to exercise labels, not a calibrated judgment.

## Outcome scoring

The evaluator is a separate role and model that applies the same v0.2 codebook and v2 contract one behavior at a time. Each call sees only the dialogue up to that behavior's decision turn: no later turns, condition, profile, coaching, answer key, final artifact or prescribed opportunity status. Behavior scores therefore cannot be influenced by hindsight or by whether the final answer was right. Final-artifact correctness (arithmetic, source references) is checked mechanically and reported separately. Consequently offline profile comparisons and coaching effects are meaningless as scientific estimates, including when an apparent gain happens by chance.

## Analysis and human review

The unit of pairing is one profile variant × task pair × orientation × replicate. A single pre-score is reused across all four siblings. Profile-group summaries combine configured variants but raw rows preserve variant identity. Turns, rubric items and sibling branches are not independent learners.

Primary rows report per-task percentage of available points, gain, and coached-minus-control gain. A separate column restricts the contrast to identical scorable behavior sets across pre, treatment and control. Missing branches are explicitly counted. Neither denominator changes nor API failures are interpreted as learning.

Bootstrap summaries sample whole task-pair clusters with replacement, retaining all observations in a sampled cluster. Identical deterministic cluster draws are used across condition summaries. Intervals are withheld with fewer than two usable pairs. The supplied pilot includes artificial calibration fixtures: use the primary-pair subset or a separately configured substantive task bank for effect reporting. Two or a handful of pairs is still limited task-level evidence; no power or coverage guarantee is asserted.

The human template has one row per blinded record × behavior. Copy it for independent raters; the runner does not overwrite an existing template during resume/export. Sample a subset stratified by conditions, profiles, behaviors and forms using the private manifest, then share only the selected blinded packets and blank labels. Preserve original human judgments before adjudication. Agreement treats N/A as a fourth nominal category; percentage scoring treats it as unavailable. These are different uses by design.

A second evaluator family can receive the identical blinded packets using the same score contract. Store its scores separately; compare item-level disagreements against humans and recompute paired estimates after joining through the private manifest. The current CLI compares human-style CSVs; it does not automatically provision or pay for a second evaluator. Coaching acceptability also requires independent human judgments with intervention context, not learner acceptance alone.

## Validation gates

| Gate | Repository support | External evidence still required |
| --- | --- | --- |
| Branch isolation | Deep copies, shared root hash, distinct sessions/directories, mutation tests | Inspect representative live trajectories |
| Information isolation | Allowlisted payload builders, audit checks, blinding tests | Audit custom adapter code and actual provider prompts |
| Opportunity handling | Explicit decision points, disclosure, accurate/no-trigger/incomplete fixtures, N/A validation | Accept rubric adaptation and calibrate ambiguity cases |
| Profile fidelity | Candidate variants, repeated samples, inspectable pre-task logs | Independent humans review error plausibility and compliance |
| Adaptation sanity | History retained; no forced update; no intervention and refusal possible | Matched/irrelevant advice pilots; allow no improvement |
| Evaluator calibration | Evidence validation, mechanical checks, blank labels and agreement tool | Two independent raters; outcome evaluator agreement |
| Operational reliability | Fixed retries, checkpoints, accepted-response replay, budgets, failure exports | Provider-specific reliability, usage and cost pilot |

Set acceptance thresholds after development pilots and before opening held-out evaluation. Keep the validated assessor, outcome evaluator, exercise bank, all role models/settings and failure policy fixed across comparisons. Family separation reduces one possible dependency; it does not prove unbiased evaluation. No numeric gate is invented by this implementation.

## Deliberate MVP limits

One substantive matched pair is included; further held-out pairs require team authorship and review. Exercise delivery is fixed bank text rather than generative adaptive coaching. There is no UI, tool-using learner, automatic memory updater, human population model, or persistent weight update. Scientific validation remains separate from passing software tests. These choices keep the guide's first complete four-branch milestone inspectable and reproducible.
