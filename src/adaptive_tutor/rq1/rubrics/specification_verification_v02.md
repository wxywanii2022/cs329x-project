# Specification and Verification Behaviors — v0.2

## Version and status

Specification and Verification Behaviors — v0.2, frozen at 2026-10-27T08:58:27.208085+00:00 by explicit user authorization for the exploratory Codex run. User approval is recorded; separate approval from Annotator B has not been documented. The substantive rules are unchanged from the proposed v0.2. Original pilot labels remain versioned separately.

## 1. Purpose and unit

Label a user's behavior at a particular decision point, not the user's general skill. Each row is one user turn × one assigned behavior. Label only that behavior. A 0 means a visible opportunity was missed at that event; it does not mean the person lacks a skill.

## 2. Allowed evidence

Use only the visible task instructions and dialogue up to and including the judged user turn. Do not use later turns, browse for additional evidence, inspect unavailable attachments, or use task rubrics as if they were user instructions. Ignore empty user messages and messages beginning with /. Do not infer facts from filenames or an agent's claim to have read a file.

## 3. Available instruction context

An untruncated, self-contained task request is the available instruction context unless it refers to inaccessible requirements/sources or the record gives a reason to think relevant instructions are missing. The absence of a separate original-task field in metadata is not, by itself, a reason to label every request N/A. A cut-off request, 'help with this task' without the task, or reliance on an unseen brief can make the case unjudgeable. Do not reconstruct missing material.

## 4. Label meanings

2 = clearly performed, with enough specificity to identify what is required, checked, or corrected. 1 = partly performed: generic, vague, or incomplete. 0 = a concrete opportunity is visible and the user does not perform the behavior. N/A = no opportunity is visible, or missing information prevents a judgment. Give a one-sentence reason for every label, including N/A.

## 5. Decision order

First identify the assigned behavior and its decision point. If the current turn visibly performs that behavior, score it 1 or 2 using the behavior-specific criteria; unrelated missing material does not erase visible behavior. If it does not perform the behavior, distinguish 0 from N/A: use 0 only when the opportunity and relevant instruction context are judgeable. Otherwise use N/A. For B4, first establish a problem in an agent output; merely supplying input is not enough.

## 6. Specificity and prior context

Read the current user turn in the visible prior context to resolve references such as 'that figure' or 'the question I mentioned'. For 1 versus 2, ask whether another reader could identify what to check or change, or which output properties are required, without guessing. Exact replacement wording is not always necessary. The current turn must itself perform or complete the behavior; do not give it credit solely because the user performed the behavior earlier.

## 7. Cross-turn completion

A user can complete a previously vague instruction by naming its target after a clarifying question. Judge each turn using only what was visible then: the earlier vague turn can remain 1 while the later, now-specific turn is 2. Do not retrospectively upgrade earlier turns. Apply the sampling cap so repeated corrections do not dominate.

## 8. B1 — decision point

Stating deliverable requirements: the opening task request or a request for a new or revised output. Requirements include format, length, audience, required content, layout, constraints, or acceptance conditions. A greeting or generic help request with no visible task does not establish a judgeable deliverable request.

## 9. B1 — labels

2: at least two concrete output properties. 1: one concrete property, or only vague qualities such as 'professional'. 0: a judgeable deliverable request with no properties, where the available task context does not already supply them. N/A: no deliverable request is established, essential requirements are only in unseen material, or the user makes no new specification and the visible task already fully specifies the requested output. If the current user explicitly states requirements, score that visible statement under 1/2 even if some requirements also appear in the task.

## 10. B1 — scope

Do not require every possible property: a request can earn 2 without a length limit or audience if it names two other concrete properties. Missing attachments do not force N/A when the visible request itself gives enough judgeable requirements. Example: 'Give me a two-column comparison for first-year students' specifies structure and audience.

## 11. B2 — decision point

Stating evidence requirements: a request for an output containing factual claims, figures, or analysis. Score how the user asks claims to be supported, not merely how many metrics or output fields they list.

## 12. B2 — labels

2: a specific, usable evidence requirement, such as a named source, a task-relevant source type, a source/date field for each figure, a requested calculation, or an explicit justification method. 1: a broad accuracy or evidence instruction without a usable support standard, such as 'be accurate', 'use reliable sources', or 'use publicly available web data'. 0: a judgeable evidence-dependent request with no support requirement, where the available task context does not already supply the evidence. N/A: no factual/analytical output is requested, sources are already supplied and no additional evidence behavior is requested or performed, or missing relevant instructions prevent distinguishing an omission from supplied evidence.

## 13. B2 — sources versus requirements

Providing the underlying dataset or source material is different from requiring a kind of source or an audit trail. A request to use official inspection reports for each incident is a specific source-type requirement even without a URL. 'Search the web' alone is broad. A visible request to show calculations or cite every estimate can earn 2 even when the dataset is already supplied. Listing output metrics or a time period alone is not an evidence requirement.

## 14. B3 — decision point

Selecting a claim to check: a response to an agent output containing a concrete, checkable substantive claim. This includes factual or numerical statements, analytical conclusions, explanations, and substantive claims of correctness such as a calculation passing a specified test. It does not include merely asking where a file is, whether a download is available, or how to open it.

## 15. B3 — labels

2: selects a particular substantive claim and checks it or asks for verification, justification, recalculation, or the conditions under which it holds. 1: requests a general re-check, including a broad category such as 'check all citations', without selecting a particular claim or reference. 0: the agent has made a substantive checkable claim and the user accepts it, moves on, or asks only a delivery/access question. N/A: no substantive checkable claim is visible yet, essential target context is missing, or the session ends before any user response.

## 16. B3 — boundaries

A file-delivery question does not count as selecting a substantive claim. If the preceding output contains only a file location or progress update, use N/A rather than 0. If it also contains factual results, a delivery-only reply can be 0. A precise user reference to an earlier claim can establish the target even if the full artifact is unavailable; record the visibility limitation and do not pretend to have checked the artifact. Asking why a particular scoring rule applies can count as verification; the user need not accuse the agent of being wrong.

## 17. B4 — decision point

Correcting an output after finding a problem: a specific problem in an agent output is visible at or before the judged user turn. Evidence may be the user's report, an agent admission, a contradiction with visible instructions, or a failed tool check of a produced artifact. The user does not have to discover the problem independently, and the annotation does not assign fault.

## 18. B4 — labels

2: identifies the problem and gives a correction or a clear acceptance condition, so another reader can tell what would count as fixing it. A directly implied correction is enough when it does not require guessing. 1: expresses dissatisfaction or points toward a problem but leaves the target or needed correction unclear. 0: a problem in an output is visible and the user does not address it. N/A: no output problem is established, or the apparent issue is only missing input, access setup, or a task that has not produced an output yet.

## 19. B4 — correction versus setup

Uploading missing reference material and asking to resume does not, by itself, count as correcting an output. A tool failure counts when it establishes a problem in a produced artifact or a claimed result; a failure to open the user's input is not automatically B4. If the agent produces an answer using the wrong inputs and the user identifies that answer as wrong, that can establish a B4 opportunity.

## 20. B4 — clarification versus correction

Adding a new preference is normally B1, not automatically B4. A user who explicitly identifies a problem in the existing output and requests a change can perform B4 even if the relevant constraint is clarified in that same turn. Do not treat the newly clarified constraint as evidence that the user missed an opportunity earlier. Example: 'This table is too wide for the page; split it into two tables' identifies both a present problem and a fix.

## 21. Corrections and truth

We annotate the visible attempt to check or correct, not whether the user's domain belief is ultimately true. Do not conduct external fact-checking to score the behavior. If the user's correction itself conflicts with visible evidence, note that limitation in the reason or unclear_rule rather than inventing an outcome. Only judge the assigned behavior; an access problem can be relevant to B4 without making a delivery question count as B3.

## 22. Recording

Required fields: session_id (source folder ID), turn_id (released user-event ID), behavior (B1–B4), label (2/1/0/N/A), reason (one sentence), confidence (high/medium/low), unclear_rule (empty unless needed). A turn assigned multiple behaviors gets separate rows and separate reasons. Keep the required session ID for linkage, but do not copy names, paths, filenames, account details, or other identifying strings into reasons. Paraphrase instead.

## 23. Confidence

High: the visible evidence and rule clearly settle the label. Medium: a reasonable contextual interpretation is needed or material is missing but the classification remains defensible. Low: a rule boundary or evidential ambiguity could plausibly change the label. N/A can have high confidence when truncation or the absence of a decision point is clear. Confidence is not a substitute for explaining uncertainty.

## 24. Sampling

Use sessions with at least two valid user turns and stratify by agent. Take at most two decision points per behavior per session. The approximate main-round target remains 60 points, around 15 per behavior, adjusted after pilots. Record the randomization and screening procedure; do not choose cases based on desired labels or agreement. A sampled candidate can be N/A after screening. The existing two pilots used different documented selection procedures and are not representative frequency estimates.

## 25. Pilot and freeze

Compare independently assigned pilot labels before discussion. For disagreements, distinguish unclear rules from genuinely difficult cases, record reasons, and revise before freezing. Pilot 2 uses new cases; if substantive rule issues remain, revise and run another new pilot. Approve and freeze a version before main annotation. Do not change frozen rules during the main round. This copy of v0.2 is frozen by the authorization recorded in the version/status section; no claim of separately documented approval from both annotators is made.

## 26. Adjudication and versioning

Preserve original independent labels and report raw agreement and unweighted Cohen's kappa before adjudication. Record a discussed final label separately. Do not infer adjudication from matching A/B labels. If v0.2 changes an old pilot label, store the new result with its protocol version rather than overwriting the original. AI-proposed labels reviewed by a human must not be reported as independently produced human-only labels.

## 27. LLM evaluation

Give the LLM the exact same approved frozen protocol and visible item context as the human raters, in a fresh context without their labels, reasons, discussion notes, or adjudications. Record provider/model/version, supported generation settings, protocol/input hashes, and outputs. Compare LLM with A, B, and adjudicated labels separately; report raw agreement, unweighted kappa, and disagreement patterns. Count N/A as a fourth nominal category, not as a blank. Keep rounds and label versions separate. Evaluation on the 20 discussed pilots is exploratory, not a held-out main test.

## 28. LLM and artifact limits

No external browsing, hidden attachments, later dialogue, or other raters' labels may be added to the LLM's input. A model error, refusal, or malformed response is a failed labeling attempt, not an N/A annotation. Do not report same-protocol agreement against older human labels if the governing rules changed; collect a separately versioned reference or clearly describe the comparison as cross-version.
