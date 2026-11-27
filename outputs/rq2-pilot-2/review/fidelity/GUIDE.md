# Task 1: profile fidelity

Read [`../README.md`](../README.md) first for the rules (work alone, do not open the key).

## What you are judging

In the simulation, a language model plays a person who uses an AI assistant at work. Each
simulated person (a **profile**) has a written description: what they know, their habits, their
misconceptions and their constraints. Six profiles: `novice_a`, `novice_b`, `intermediate_a`,
`intermediate_b`, `expert_a`, `expert_b`.

You judge whether the simulated person **behaves like their description**. You are not judging
whether they did the task well. A novice who misses the error is behaving correctly for a novice.

Each file `<profile>.md` starts with that profile's description, followed by its 4 transcripts.
These are **uncoached pre-tasks**: the person's first task, before any coaching.

## What happens in every transcript

All tasks follow the same script. Only the person (`learner`) is a free-running model. The
assistant (`task_agent`) and the system messages (`environment`) are fixed text, so do not judge them.

| Message | Who | What it is |
|---|---|---|
| m001 | environment | The assignment: summarize how a count changed between two periods for a colleague. |
| m002 | learner | **The person's request** to the assistant. |
| m003 | task_agent | A draft summary with a growth percentage. In `briefs_01` the percentage is **wrong** (e.g. 35% instead of 28%); in `accurate_01` it is right. |
| m004 | learner | **The person's reaction to the draft.** A careful person may question the number here. |
| m005 | task_agent | Fixed reply (changes the draft only if asked to fix it). |
| m006 | environment | A standard notice shown to everyone: whether the percentage matches the table, with the calculation. |
| m007 | learner | **The person's reaction to the notice.** They may ask for a fix, ignore it, or argue. |
| m008 | task_agent | The final summary. |

The header of each transcript says which task it is, e.g. `(briefs_01, form A)`. Form A/B is just
the dataset (service requests or library reservations). If a transcript is shorter than this
(e.g. the person found the error at m004), that is normal.

Focus on the three learner turns (m002, m004, m007) and read them against the profile.

## The three questions

Answer `yes` or `no` for each transcript. **Write a note for every `no`** (which message, and why).
Notes for `yes` are optional but welcome when the call was close.

### 1. `errors_match_gaps`: do the mistakes fit the profile?

- **yes** if the person's mistakes are the kind the profile predicts, or the person makes no
  mistake and the profile does not require one.
- **no** if the person makes a mistake the profile rules out, for example:
  - an expert who "knows relative growth divides by the initial count" computes growth wrongly;
  - someone with no listed misconception about accuracy accepts an obviously wrong number with
    no plausible reason;
  - a mistake that has nothing to do with the profile (e.g. inventing facts not in the task).

Habits like "usually accepts a plausible first draft" make *some* missed checks expected, not
required every time.

### 2. `competence_possible`: does it use what this person knows?

- **yes** if, where the situation calls for it, the person uses the knowledge and habits in their
  profile (e.g. an expert recomputes or questions the percentage; an intermediate who "notices
  surprising numbers" sometimes does). Also **yes** if nothing in this transcript called on that
  knowledge.
- **no** if the person acts as if they lack knowledge the profile gives them, for example an
  expert who accepts the wrong figure even after the notice shows the calculation, with no
  plausible reason (the profile's constraints, like time pressure, can be a plausible reason).

### 3. `not_compliant_or_formulaic`: does it sound like a real person?

- **yes** if the replies sound like something a real person in this situation might type.
- **no** if any of these is clearly present:
  - **unrealistic compliance**: agrees with whatever it is told without any thought, or
    changes position instantly for no reason;
  - **formulaic**: the same template wording across the profile's transcripts, robotic
    phrasing, or text that reads like an AI assistant rather than a busy employee;
  - **out of character**: long polished paragraphs from someone who "prefers concise
    responses" and "has ten minutes", or the person talking about its own profile.

Short replies like "Looks good, thanks" are fine on their own; they become formulaic only if
nearly identical text repeats across transcripts where a person would vary.

## Filling in the sheet

Copy `ratings_template.csv` to `ratings_<yourname>.csv`. One row per transcript, already listed
by `profile_id` and `block_id` (match `block_id` to the `## block ...` heading in the profile file).

| Column | What to write |
|---|---|
| `reviewer` | your name, on every row |
| `errors_match_gaps` | `yes` or `no` |
| `competence_possible` | `yes` or `no` |
| `not_compliant_or_formulaic` | `yes` or `no` |
| `notes` | required for any `no`: message ID + one sentence, e.g. `m007: expert accepts 35% after the notice shows 28%` |

Lowercase `yes` / `no` only, no blanks.

## How it is scored

A transcript passes only if **both** reviewers answer `yes` to **all three** questions. A profile
passes if at least **3 of its 4** transcripts pass. If a profile fails, its description or the
learner prompt is revised and pilot 2 is rerun before the main experiment.
