# Coach no-gap check (full condition)

Recorded full-condition coach requests re-sent with the same prompt, model and seed, except that every assessor label 0 or 1 is rewritten to 2. The messages are unchanged, and the prompt tells the coach to check the assessment against them. Original decisions: exercise:48.

| blocks | n | none | exercise targets |
|---|---|---|---|
| all | 48 | 7/48 | B1:1, B2:21, B3:18, B4:1
| without_assessment coach also chose none on these messages | 20 | 3/20 | B2:8, B3:9
| without_assessment coach chose an exercise | 28 | 4/28 | B1:1, B2:13, B3:9, B4:1
