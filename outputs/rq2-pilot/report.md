# RQ2 live pilot report

Runs: 12 shards, 48 blocks with block.json. Development tasks only; screening flags are lexical pointers to transcripts, not labels; nothing here is an effect estimate.

## Run status

| run | blocks | failed branches | failed scores | audit | call failures | transport retries |
|---|---|---|---|---|---|---|
| smoke | 1 | 0 | 0 | passed | 0 | 0 |
| expert_a.accurate_01 | 4 | 0 | 0 | passed | 0 | 0 |
| expert_a.briefs_01 | 4 | 0 | 1 | passed | 1 | 0 |
| expert_b.accurate_01 | 4 | 0 | 0 | passed | 0 | 0 |
| expert_b.briefs_01 | 4 | 0 | 1 | passed | 1 | 0 |
| intermediate_a.accurate_01 | 4 | 0 | 1 | passed | 1 | 0 |
| intermediate_a.briefs_01 | 4 | 0 | 1 | passed | 1 | 0 |
| intermediate_b.accurate_01 | 4 | 0 | 0 | passed | 0 | 0 |
| intermediate_b.briefs_01 | 4 | 0 | 0 | passed | 0 | 0 |
| novice_a.accurate_01 | 4 | 0 | 0 | passed | 0 | 0 |
| novice_a.briefs_01 | 4 | 0 | 1 | passed | 1 | 0 |
| novice_b.accurate_01 | 4 | 0 | 0 | passed | 0 | 0 |
| novice_b.briefs_01 | 4 | 0 | 0 | passed | 0 | 0 |

## Calls per role

| role | accepted calls | median latency s | mean output tokens | max output tokens |
|---|---|---|---|---|
| learner | 1008 | 1.3825 | 38 | 108 |
| assessment | 192 | 231.2155 | 2110 | 10566 |
| coach | 144 | 2.258 | 90 | 139 |
| evaluator | 944 | 32.782 | 2417 | 9707 |

Call failures:

| role | error | count |
|---|---|---|
| evaluator | Evidence quote not in cited turn | 5 |

## v0.2 fixtures (13 constructed items; not an accuracy estimate)

| run | n | raw | κ | false-missed | failed | disagreements |
|---|---|---|---|---|---|---|
| fixtures-assessor-v2-qwen38-27b-s329 | 13 | 0.846 | 0.772 | 0 | 0 | F01 B1 ref 0→N/A, F04 B2 ref 0→N/A |
| fixtures-evaluator-gpt-oss-20b-s329 | 13 | 0.769 | 0.672 | 1 | 0 | F01 B1 ref 0→1, F13 B2 ref N/A→0, F07 B3 ref 1→2 |

## Learner behavior on the uncoached pre-task

One row per profile; pre-tasks are shared by the block's four branches. Spontaneous check = the scripted agent recognized a targeted check of the draft before the disclosure; states correct = the review message itself gives the correct growth figure; early correction = named the error and asked for a fix at review; final correct = the final artifact's figure matches the table.

| profile | pre-tasks | spontaneous check | states correct | early correction | final correct | false alarm (accurate) | asks evidence | request words | review words | request similarity | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| novice_a | 8 | 0/4 | 0/4 | 0/4 | 3/4 | 0/4 | 0/8 | 23 | 12 | 0.39 | none |
| novice_b | 8 | 1/4 | 1/4 | 0/4 | 3/4 | 0/4 | 0/8 | 21.5 | 11 | 0.45 | none |
| intermediate_a | 8 | 2/4 | 2/4 | 0/4 | 4/4 | 0/4 | 0/8 | 28.25 | 17.5 | 0.33 | none |
| intermediate_b | 8 | 1/4 | 2/4 | 0/4 | 2/4 | 0/4 | 0/8 | 29.125 | 21.125 | 0.37 | none |
| expert_a | 8 | 1/4 | 2/4 | 0/4 | 3/4 | 0/4 | 0/8 | 25.875 | 21.625 | 0.4 | none |
| expert_b | 8 | 2/4 | 2/4 | 1/4 | 4/4 | 0/4 | 0/8 | 25.625 | 19.375 | 0.37 | none |

### Pre-task labels by reporting group (briefs/incorrect-growth tasks)

Counts of 2/1/0/N/A. Look for overlapping but different patterns, not a perfect ranking.

| labels from | group | pre-tasks | B1 | B2 | B3 | B4 |
|---|---|---|---|---|---|---|
| assessor | novice | 8 | 2:2 1:6 | 2:7 N/A:1 | 2:3 1:1 0:4 | 2:7 N/A:1 |
| assessor | intermediate | 8 | 2:4 1:4 | 2:6 N/A:2 | 2:5 0:3 | 2:8 |
| assessor | expert | 8 | 2:3 1:5 | 2:6 0:1 N/A:1 | 2:4 0:4 | 2:6 N/A:2 |
| evaluator | novice | 8 | 2:3 1:3 N/A:1 missing:1 | 2:6 N/A:1 missing:1 | 2:4 0:3 missing:1 | 2:6 N/A:1 missing:1 |
| evaluator | intermediate | 8 | 2:6 1:2 | 2:4 0:4 | 2:5 0:3 | 2:7 1:1 |
| evaluator | expert | 8 | 2:5 1:3 | 2:3 0:4 N/A:1 | 2:4 0:4 | 2:7 N/A:1 |

### Assessor (Qwen v2) vs evaluator on the same pre-task decision points

Two different models applying the same codebook; agreement is not accuracy.

| behavior | n | exact agreement | κ |
|---|---|---|---|
| B1 | 47 | 27/47 | 0.171 |
| B2 | 47 | 31/47 | 0.313 |
| B3 | 47 | 42/47 | 0.8 |
| B4 | 47 | 44/47 | 0.873 |
| all | 188 | 144/188 | 0.642 |

## Coaching decisions

Targets assessor gap = the chosen exercise's behavior was labeled 0 or 1 by the pre-task assessor (the without_assessment coach never saw those labels).

| condition | check_v1 | correct_v1 | evidence_v1 | specify_v1 | targets assessor gap | coaching status |
|---|---|---|---|---|---|---|
| full | 25 | 18 | 0 | 5 | 22/48 | complete×48 |
| without_assessment | 16 | 18 | 14 | 0 | 11/48 | complete×48 |
| without_background | 26 | 18 | 1 | 3 | 22/48 | complete×48 |

Learner practice replies: 288, mean 26.976 words.

## Post-minus-pre gain (briefs_01, evaluator, percentage points; descriptive only)

| group | full | without_assessment | without_background | no_coaching |
|---|---|---|---|---|
| novice | 2.976 (n=7) | 6.548 (n=7) | 1.786 (n=7) | -5.952 (n=7) |
| intermediate | 14.286 (n=7) | 21.875 (n=8) | 19.271 (n=8) | 17.708 (n=8) |
| expert | 23.958 (n=8) | 23.81 (n=7) | 20.833 (n=8) | 19.643 (n=7) |

## Transcripts

Every dialogue is in `transcripts/<profile>.md`.

