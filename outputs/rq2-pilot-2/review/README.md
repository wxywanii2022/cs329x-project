# Pilot 2 human review: start here

Two annotators (call them A and B) do two independent tasks on pilot 2. Together they decide
whether the simulation is good enough to freeze the preregistration and run the main experiment
(gates in `docs/rq2-preregistration-draft.md`, section 6).

| | Task 1: profile fidelity | Task 2: evaluator calibration |
|---|---|---|
| Question | Does each simulated learner behave like the person its profile describes? | Does the evaluator model label behaviors the way people do? |
| You read | 24 short transcripts (6 profiles × 4) | 80 short dialogue excerpts (20 per behavior B1–B4) |
| You answer | 3 yes/no questions per transcript | one label (2 / 1 / 0 / N/A) and a one-line reason per excerpt |
| Guide | [`fidelity/GUIDE.md`](fidelity/GUIDE.md) | [`evaluator/GUIDE.md`](evaluator/GUIDE.md) |
| Material | `fidelity/<profile>.md` | `evaluator/items.md` |
| Your answer sheet | copy of `fidelity/ratings_template.csv` | copy of `evaluator/labels_template.csv` |
| Time (rough) | 1–1.5 hours | 3–4 hours |
| Pass rule | a transcript passes if both readers say yes to all 3; a profile passes with ≥ 3 of 4 | evaluator vs adjudicated labels: κ ≥ 0.60 overall, every behavior ≥ 0.40, false-missed ≤ 10% |

Either task can be done first. Task 2 is the larger one.

## Rules for both tasks

1. **Work alone.** Do not talk about items, labels or impressions with the other annotator until
   both of you have sent in both sheets. Agreement is only meaningful if the labels are independent.
2. **Do not open `evaluator/key.private.csv`** or anything under `outputs/rq2-pilot-2/shards/`,
   `smoke/` or `fixtures-*`. They contain the model's labels, the conditions and the profiles behind
   each excerpt. The key is not in Git; keep it that way.
3. **Do not change the material.** Fill in only your own copy of the template.
4. **Answer from what is written.** Do not look up facts, run calculations to "grade" the learner,
   or guess at what happened later in a dialogue.
5. **If you are unsure, still answer**, and say why in the notes/reason column. Blank cells count
   as missing.

## Workflow

1. Copy the templates and put your name in the file names:
   `fidelity/ratings_<name>.csv` and `evaluator/labels_<name>.csv`. Fill in the
   `reviewer` / `annotator` column on every row.
2. Do the tasks following the two guides.
3. Send both CSV files to the coordinator (Yuan) **directly, not through Git**, so neither
   annotator can see the other's answers before finishing.
4. The coordinator computes agreement (human vs human, and evaluator vs each human) before any
   discussion and shares the numbers.
5. **Adjudication (task 2 only):** A and B meet and go through only the items where they
   disagreed. For each, agree on a final label and a one-line reason. Your original labels are
   kept unchanged; the final labels go in a separate file `evaluator/labels_adjudicated.csv`
   with the same columns (annotator = `adjudicated`).
6. The coordinator compares the evaluator with the adjudicated labels and checks the pass rules.
   Then all sheets are committed together.
