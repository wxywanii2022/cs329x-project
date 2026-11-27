# Coach no-gap check (full condition)

Recorded full-condition coach requests re-sent with the same prompt, model and seed, except that every assessor label 0 or 1 is rewritten to 2. The messages are unchanged, and the prompt tells the coach to check the assessment against them. Original decisions: exercise:48.

| blocks | n | none | exercise targets |
|---|---|---|---|
| all | 48 | 47/48 | B2:1
| without_assessment coach also chose none on these messages | 20 | 20/20 | 
| without_assessment coach chose an exercise | 28 | 27/28 | B2:1

Among 48 decisions that received an assessment, 1 exercises target a behavior the sent assessment labeled 2 or null.
