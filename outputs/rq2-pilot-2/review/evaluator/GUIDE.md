# Task 2: evaluator calibration

Read [`../README.md`](../README.md) first for the rules (work alone, do not open the key).

## What you are doing and why

In the main experiment, a model (the **evaluator**) scores how well each simulated person
specifies and verifies work with an AI assistant. Before we trust it, we check it against people:
you label 80 excerpts from pilot 2 with the same codebook the evaluator uses, and we compare.

Each excerpt is a dialogue **cut off at one user turn**, marked ▶. You label **one behavior** for
that turn (named in the heading, e.g. `E002 · B1`). Ignore the other behaviors for that item.

The full rules are codebook v0.2:
`src/adaptive_tutor/rq1/rubrics/specification_verification_v02.md` (about 10 minutes to read).
**Read it once before you start.** This guide summarizes it for these tasks; if the two ever
seem to differ, the codebook wins.

## Reading an item

```
## E002 · B1                      ← item ID · behavior to label
- m001 evidence: Task assignment: ...      ← what the person was asked to do (visible to them)
- ▶ m002 user: Hey, can you summarize ...  ← the turn you label
```

- **evidence** = the task assignment or a system notice. The person can see it.
- **user** = the person. **assistant** = the AI task assistant.
- The excerpt stops at ▶ on purpose. Judge only what is visible up to and including that turn.
- The assignment never names the table or gives the numbers; the person only sees the goal.
- All tasks are the same kind: summarize how a count changed (e.g. completed service requests,
  September to October) for a colleague. The assistant's draft states a growth percentage, which
  may be wrong. A later system notice ("Standard evidence disclosure: ...") says whether the
  percentage matches the table and shows the calculation.

Items come from different points of the dialogue: B1 and B2 items end at the person's first
request; B3 items end at their reaction to the draft; B4 items end at their reaction to the notice.

## Labels

| Label | Meaning |
|---|---|
| **2** | clearly performed, specific enough that another reader knows exactly what is required, checked or corrected |
| **1** | partly performed: generic, vague or incomplete |
| **0** | there was a concrete, visible opportunity and the person did not do it |
| **N/A** | no opportunity is visible, or something missing makes it impossible to judge |

A 0 is about this one moment, not about the person's skill.

## Decision steps (every item)

1. Find the behavior's **decision point** (table below). Is it present at ▶?
2. If the ▶ turn **does** the behavior: choose **2 or 1** by specificity.
3. If it **does not**: choose **0** if the opportunity is real and judgeable, otherwise **N/A**.
4. Write a one-sentence reason. For N/A, also pick the reason code.

## The four behaviors

### B1: stating deliverable requirements (▶ = the request for an output)

Requirements are properties of the output: format, length, audience, required content, layout,
constraints, acceptance conditions.

| Label | Rule |
|---|---|
| 2 | at least **two** concrete output properties |
| 1 | **one** concrete property, or only vague qualities ("professional", "good") |
| 0 | a judgeable request with **no** properties, and the task does not already supply them |
| N/A | no deliverable request, or the visible task already fully specifies the output and the user adds nothing |

Notes: what counts is what the user states in this turn. A request that only restates the topic
and period from the assignment adds no property (see the first worked example below).

### B2: stating evidence requirements (▶ = a request for an output with facts or figures)

This is about **how the user asks the claims to be supported**, not how many figures they want.

| Label | Rule |
|---|---|
| 2 | a specific, usable support requirement: a named source, a task-relevant source type, a source for each figure, a requested calculation, or an explicit justification method |
| 1 | a broad accuracy instruction with no usable standard ("make sure it's accurate", "use reliable data") |
| 0 | a judgeable fact/figure request with **no** support requirement, where the task does not already supply the evidence |
| N/A | no factual output requested, or the sources are already supplied and no extra evidence behavior is requested, or missing context prevents a judgment |

Notes: supplying data is not the same as requiring a kind of support. Listing metrics or a time
period alone is not an evidence requirement. "Show the calculation" earns 2 even when the data is
supplied.

### B3: selecting a claim to check (▶ = the reaction to an assistant output with a checkable claim)

| Label | Rule |
|---|---|
| 2 | picks a **particular** claim (e.g. "the 35%") and checks it or asks for it to be verified, justified or recalculated |
| 1 | asks for a **general** re-check ("can you double-check this?") without picking a claim |
| 0 | the assistant made a checkable claim and the user accepts it, moves on, or asks only about delivery |
| N/A | no checkable claim visible yet (e.g. the assistant only asked a question) |

Notes: the user does not have to say the claim is wrong; asking how a figure was computed counts.
For 1 versus 2, ask whether another reader could tell which claim to check without guessing.

### B4: correcting an output after a problem (▶ = the turn after a problem became visible)

First ask: **is a specific problem in an assistant output visible** at or before ▶? The system
notice saying the percentage conflicts with the table establishes one. The user does not have to
find it themselves.

| Label | Rule |
|---|---|
| 2 | identifies the problem **and** gives a correction or clear acceptance condition (e.g. "change it to 28%", "fix the percentage to match the calculation"); a directly implied fix is enough |
| 1 | points toward the problem or expresses dissatisfaction, but the needed correction is unclear |
| 0 | a problem is visible and the user does not address it (e.g. "Looks good, send it") |
| N/A | no problem is established (e.g. the notice says the percentage **agrees** with the table) |

Notes: we label the attempt, not whether the user's own number is right. A user who confidently
"corrects" to a wrong value still attempted a correction; mention the conflict in the reason.

## Worked examples (the team's constructed fixtures, same kind of task)

| Behavior | Turn (shortened) | Label | Why |
|---|---|---|---|
| B1 | "Can you help me summarize how completed service requests changed?" | 0 | judgeable request, no output properties, none supplied by the task |
| B1 | asks for a one-page email with three bullets | 2 | two properties: format and structure |
| B2 | "Can you help me summarize how completed service requests changed?" | 0 | figures requested, no support requirement, no source given to the user |
| B2 | "...and make sure the numbers are accurate." | 1 | broad accuracy instruction without a usable standard |
| B2 | "Show the calculation and say which table each number comes from." | 2 | requested calculation plus a source for each figure |
| B2 | "...using the official monthly operations counts for both months." | 2 | task-relevant source type |
| B3 | assistant only asks a clarifying question | N/A | no checkable claim |
| B3 | "Can you double-check this?" | 1 | general re-check, no claim selected |
| B3 | asks for the 35% to be recalculated | 2 | targets the specific claim |
| B4 | notice says the draft agrees with its calculation | N/A | no problem visible |
| B4 | after the notice shows a conflict, user leaves the draft as is | 0 | visible problem not addressed |
| B4 | "The 35% is wrong, it should be 28%." | 2 | names the problem and the fix |

## Filling in the sheet

Copy `labels_template.csv` to `labels_<yourname>.csv`. Rows are already listed by `item_id` and
`behavior`; do not reorder or change them.

| Column | What to write |
|---|---|
| `annotator` | your name, on every row |
| `label` | `2`, `1`, `0` or `N/A` (exactly these) |
| `na_reason` | only when the label is N/A: `no_opportunity` or `insufficient_evidence`; otherwise leave empty |
| `reason` | one sentence that cites the turn, e.g. `m004 asks to recheck the 35% figure specifically` |

Put a reason containing commas in double quotes, or just avoid commas.

## Tips

- Expect many short items (just the first request). Do not speed through them: small wording
  differences decide B1 and B2.
- If a case sits on a rule boundary, pick the label the codebook supports best and write
  `boundary:` at the start of the reason. These are useful in adjudication.
- Take a break every 20 items; consistency drops when tired.
- Do not change earlier answers after seeing later items unless you misread the rule; if you do,
  note it in the reason.
