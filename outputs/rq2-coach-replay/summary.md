# Coach prompt replay

Same recorded inputs, only the system prompt differs. Gap = the assessor labeled the chosen behavior 0 or 1; label 2 = the exercise targets a behavior the assessor scored as performed. No-gap blocks = the assessor gave no 0 or 1 at all. The without_assessment coach never saw these labels, so its numbers measure agreement with the assessor, not instruction following.

## By condition

| condition | prompt | n | none | targets gap | targets label 2 | none when no gap | targets |
|---|---|---|---|---|---|---|---|
| full | v1 | 47 | 0 | 22/47 | 24/47 | 0/6 | B1:5, B3:24, B4:18 |
| full | replay | 47 | 5 | 41/42 | 1/42 | 5/6 | B1:16, B3:25, B4:1 |
| without_assessment | v1 | 48 | 0 | 11/48 | 26/48 | 0/6 | B2:14, B3:16, B4:18 |
| without_assessment | replay | 48 | 17 | 9/31 | 18/31 | 2/6 | B1:3, B2:9, B3:10, B4:9 |
| without_background | v1 | 47 | 0 | 22/47 | 25/47 | 0/6 | B1:3, B2:1, B3:26, B4:17 |
| without_background | replay | 47 | 6 | 41/41 | 0/41 | 6/6 | B1:15, B2:1, B3:25 |

## By reporting group (all coached conditions)

| reporting_group | prompt | n | none | targets gap | targets label 2 | none when no gap | targets |
|---|---|---|---|---|---|---|---|
| expert | v1 | 48 | 0 | 16/48 | 28/48 | 0/6 | B1:6, B2:5, B3:18, B4:19 |
| expert | replay | 48 | 14 | 30/34 | 3/34 | 5/6 | B1:13, B2:4, B3:16, B4:1 |
| intermediate | v1 | 48 | 0 | 19/48 | 24/48 | 0/3 | B1:1, B2:6, B3:21, B4:20 |
| intermediate | replay | 48 | 4 | 30/44 | 12/44 | 1/3 | B1:11, B2:3, B3:22, B4:8 |
| novice | v1 | 46 | 0 | 20/46 | 23/46 | 0/9 | B1:1, B2:4, B3:27, B4:14 |
| novice | replay | 46 | 10 | 31/36 | 4/36 | 7/9 | B1:10, B2:3, B3:22, B4:1 |

Decisions that changed: 92/142.
