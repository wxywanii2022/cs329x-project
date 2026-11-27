# RQ2 live pilot report

Runs: 12 shards, 48 blocks with block.json. Development tasks only; screening flags are lexical pointers to transcripts, not labels; nothing here is an effect estimate.

## Run status

| run | blocks | failed branches | failed scores | audit | call failures | transport retries |
|---|---|---|---|---|---|---|
| smoke | 1 | 0 | 0 | passed | 0 | 0 |
| expert_a.accurate_01 | 4 | 0 | 0 | passed | 0 | 0 |
| expert_a.briefs_01 | 4 | 0 | 0 | passed | 0 | 0 |
| expert_b.accurate_01 | 4 | 0 | 0 | passed | 0 | 0 |
| expert_b.briefs_01 | 4 | 0 | 0 | passed | 0 | 0 |
| intermediate_a.accurate_01 | 4 | 0 | 1 | passed | 1 | 0 |
| intermediate_a.briefs_01 | 4 | 0 | 0 | passed | 0 | 0 |
| intermediate_b.accurate_01 | 4 | 0 | 2 | passed | 2 | 0 |
| intermediate_b.briefs_01 | 4 | 0 | 0 | passed | 0 | 0 |
| novice_a.accurate_01 | 4 | 0 | 2 | passed | 2 | 0 |
| novice_a.briefs_01 | 4 | 0 | 1 | passed | 1 | 0 |
| novice_b.accurate_01 | 4 | 0 | 1 | passed | 1 | 0 |
| novice_b.briefs_01 | 4 | 0 | 3 | passed | 3 | 0 |

## Calls per role

| role | accepted calls | median latency s | mean output tokens | max output tokens |
|---|---|---|---|---|
| learner | 963 | 0.871 | 26 | 64 |
| assessment | 192 | 187.4065 | 1916 | 7901 |
| coach | 144 | 2.472 | 123 | 246 |
| evaluator | 927 | 26.598 | 2304 | 16735 |

Call failures:

| role | error | count |
|---|---|---|
| evaluator | Evidence quote not in cited turn | 10 |

## v0.2 fixtures (constructed items; not an accuracy estimate; taskv2 = 5 learner-view-v2 items, others = 13)

| run | n | raw | κ | false-missed | failed | disagreements |
|---|---|---|---|---|---|---|
| fixtures-assessor-v2-qwen38-27b-s329 | 13 | 0.846 | 0.772 | 0 | 0 | F01 B1 ref 0→N/A, F04 B2 ref 0→N/A |
| fixtures-evaluator-gpt-oss-20b-s329 | 12 | 0.833 | 0.755 | 0 | 1 | F01 B1 ref 0→N/A, F07 B3 ref 1→2 |
| fixtures-taskv2-assessor-v2-qwen38-27b-s329 | 5 | 0.8 | 0.722 | 0 | 0 | T01 B1 ref 0→N/A |
| fixtures-taskv2-evaluator-gpt-oss-20b-s329 | 5 | 0.8 | 0.706 | 0 | 0 | T01 B1 ref 0→1 |

## Learner behavior on the uncoached pre-task

One row per profile; pre-tasks are shared by the block's four branches. Spontaneous check = the scripted agent recognized a targeted check of the draft before the disclosure; states correct = the review message itself gives the correct growth figure; early correction = named the error and asked for a fix at review; final correct = the final artifact's figure matches the table.

| profile | pre-tasks | spontaneous check | states correct | early correction | final correct | false alarm (accurate) | asks evidence | request words | review words | request similarity | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| novice_a | 8 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 | 0/8 | 19.25 | 7.375 | 0.49 | none |
| novice_b | 8 | 2/4 | 0/4 | 0/4 | 4/4 | 0/4 | 0/8 | 17.625 | 9.125 | 0.47 | none |
| intermediate_a | 8 | 3/4 | 2/4 | 2/4 | 4/4 | 0/4 | 0/8 | 24 | 13.25 | 0.41 | none |
| intermediate_b | 8 | 1/4 | 0/4 | 1/4 | 3/4 | 0/4 | 0/8 | 22.125 | 12 | 0.5 | none |
| expert_a | 8 | 2/4 | 0/4 | 0/4 | 4/4 | 0/4 | 0/8 | 20.75 | 11.5 | 0.31 | none |
| expert_b | 8 | 3/4 | 2/4 | 2/4 | 4/4 | 0/4 | 0/8 | 20.375 | 15.75 | 0.41 | none |

### Pre-task labels by reporting group (briefs/incorrect-growth tasks)

Counts of 2/1/0/N/A. Look for overlapping but different patterns, not a perfect ranking.

| labels from | group | pre-tasks | B1 | B2 | B3 | B4 |
|---|---|---|---|---|---|---|
| assessor | novice | 8 | 2:4 1:4 | 2:4 1:3 0:1 | 2:3 1:1 0:4 | 2:8 |
| assessor | intermediate | 8 | 2:8 | 0:8 | 2:4 0:4 | 2:7 0:1 |
| assessor | expert | 8 | 2:5 1:3 | 2:1 1:4 0:3 | 2:4 0:4 | 2:7 N/A:1 |
| evaluator | novice | 8 | 2:1 1:6 0:1 | 2:2 1:1 0:5 | 2:4 0:4 | 2:8 |
| evaluator | intermediate | 8 | 2:7 1:1 | 0:8 | 2:4 0:3 N/A:1 | 2:8 |
| evaluator | expert | 8 | 2:6 1:2 | 1:3 0:5 | 2:4 0:3 N/A:1 | 2:7 N/A:1 |

### Assessor (Qwen v2) vs evaluator on the same pre-task decision points

Two different models applying the same codebook; agreement is not accuracy.

| behavior | n | exact agreement | κ |
|---|---|---|---|
| B1 | 46 | 28/46 | 0.208 |
| B2 | 46 | 35/46 | 0.568 |
| B3 | 46 | 34/46 | 0.56 |
| B4 | 46 | 44/46 | 0.9 |
| all | 184 | 141/184 | 0.652 |

## Coaching decisions

Targets assessor gap = the chosen exercise's behavior was labeled 0 or 1 by the pre-task assessor (the without_assessment coach never saw those labels).

| condition | check_v1 | correct_v1 | evidence_v1 | none | specify_v1 | targets assessor gap | coaching status |
|---|---|---|---|---|---|---|---|
| full | 22 | 1 | 21 | 0 | 4 | 48/48 | complete×45, declined×3 |
| without_assessment | 11 | 3 | 6 | 20 | 8 | 17/28 | complete×27, declined×1, none×20 |
| without_background | 18 | 1 | 20 | 2 | 7 | 46/46 | complete×45, declined×1, none×2 |

Learner practice replies: 243, mean 18.802 words.

## Post-minus-pre gain (briefs_01, evaluator, percentage points; descriptive only)

| group | full | without_assessment | without_background | no_coaching |
|---|---|---|---|---|
| novice | 6.25 (n=6) | 14.583 (n=6) | 15.625 (n=8) | -7.292 (n=8) |
| intermediate | 10.938 (n=8) | 8.854 (n=8) | 21.354 (n=8) | 1.042 (n=8) |
| expert | 26.562 (n=8) | 4.167 (n=8) | 13.542 (n=8) | 9.375 (n=8) |

## Transcripts

Every dialogue is in `transcripts/<profile>.md`.

