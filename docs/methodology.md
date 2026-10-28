# Implementation decisions and research gates

## Source of truth

The proposal's opening section describes four branches with retained learner history. The supplied simulator guide makes that design concrete. Older proposal text later in the same DOCX describes a two-arm study with removed personal memory; that is historical material and is not the implemented protocol. Both original DOCX files are preserved unchanged.

The simulator implements immediate transfer with retained conversational context. It makes no claim about lasting human learning or updated model weights.

## The simulator rubric adaptation

The appendix's existing rubric sometimes makes B1 N/A when requirements are fully supplied and B2 N/A when sources are supplied. The guide instead deliberately supplies requirements and a source table, then measures whether the learner communicates them to the task agent. Applying the appendix literally would remove key opportunities from every primary task.

The implementation therefore names its candidate rubric **`sim-opportunities-v1`**. Assignment constraints are learner-side instructions; the scripted task agent responds to the learner's visible request and source table, not the assignment instructions. B1 measures communicating at least two concrete properties. B2 measures a specific request for traceable source support, even though a table exists. B3 is measured before the fixed evidence disclosure. B4 is measured after disclosure so everyone has a visible correction opportunity.

This is an explicit operational choice to be accepted and calibrated by the team, not a claim of equivalence to the frozen RQ1 codebook. The assessment and outcome prompts both state it. A future validated mapping must change the prompt/data/implementation version and use a new output directory.

| Behavior | Primary decision point | 2 | 1 | 0 |
| --- | --- | --- | --- | --- |
| B1 | Initial learner request | At least two concrete deliverable properties | One property or vague qualities | No deliverable requirements |
| B2 | Initial learner request | Specific source/calc support request | Generic accuracy request | No evidence requirement |
| B3 | Learner response to draft | Specific claim selected for checking | General recheck | Accepts or moves on |
| B4 | Learner response to fixed disclosure | Specific problem plus concrete correction | Generic dissatisfaction | Leaves the disclosed issue unaddressed |

The fixture `accurate_01` still permits checking a specific claim but has no B4 problem. `no_trigger_01` supplies a preference task with no scored opportunities. `incomplete_01` deliberately has no captured dialogue, producing `insufficient_evidence` instead of zeros. These cases test observability and N/A handling; they are not primary transfer pairs.

## Controlled assistance and simulated adaptation

The task agent fixes the initial growth claim, calculates follow-up evidence deterministically, and preserves an incorrect draft unless a recognizable correction request occurs. All branches receive the same fixed disclosure even if the learner already discovered the discrepancy. Its request parsing is deliberately limited to visible lexical patterns, documented in `tasks.py`; it is not a general natural-language tutor.

The `discovery` field distinguishes spontaneous checking from prompted disclosure. `spontaneous_check_then_correction` reports that observable sequence, but the correction still occurs after standardized disclosure. It must not be described as an unprompted naturalistic correction rate. The primary B4 outcome is correction **after disclosure**. A separate naturalistic protocol would be needed to remove that disclosure.

Six candidate knowledge profiles cover three reporting groups with two variants each. Domain knowledge, response-length preference and time availability are matched. The initial date is fixed in the profile data. There is no skill counter, automatic gain, hidden memory update or instruction to achieve a target score. Real learner calls always use the same policy and their own observed history.

The mock learner samples canned responses without reference to reporting group or treatment. The mock scorer uses lexical rules to exercise labels, not a calibrated evaluator. Consequently offline profile comparisons and coaching effects are meaningless as scientific estimates, including when an apparent gain happens by chance.

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
