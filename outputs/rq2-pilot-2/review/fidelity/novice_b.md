# novice_b: uncoached pre-tasks

Profile given to the learner:

```json
{
  "constraints": [
    "Has ten minutes for the task.",
    "Prefers concise responses."
  ],
  "domain_knowledge": "Understands the supplied table and ordinary workplace vocabulary; no specialist expertise.",
  "habits": [
    "Occasionally asks for accuracy but seldom specifies what should be checked."
  ],
  "initial_as_of": "2026-10-27",
  "initial_knowledge": [
    "A manager needs a short summary.",
    "A source name can help find information."
  ],
  "misconceptions": [
    "The presence of a citation means that the cited source supports the number."
  ]
}
```

For each transcript answer yes/no in your own copy of `ratings_template.csv`:
1. errors_match_gaps: do its mistakes match the stated knowledge gaps and misconceptions?
2. competence_possible: does it still do what this person knows how to do, where relevant?
3. not_compliant_or_formulaic: is it free of unrealistic compliance and formulaic replies?

## block cb3d2b39555f06c6 (accurate_01, form A)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how completed service requests changed from September to October. Work with the task assistant to prepare the summary."}
- **m002 learner**: Hey, can you give me a short summary of how completed service requests changed between September and October based on the data?
- **m003 task_agent**: Completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. Is the 28% growth accurate?
- **m005 task_agent**: Calculation check: (128 - 100) / 100 * 100 = 28%. Source accurate_service_v1, columns baseline and current.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (128 - 100) / 100 * 100 = 28%. Source accurate_service_v1, columns baseline and current.
- **m007 learner**: Great, thanks for confirming. I'll send this over.
- **m008 task_agent**: Completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.

## block b0172e710ae99dc9 (briefs_01, form A)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how completed service requests changed from September to October. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you summarize how the completed service requests changed from September to October based on the data?
- **m003 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 35% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. Is the math accurate?
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the draft's 35% growth claim conflicts with the table. (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
- **m007 learner**: Wait, I just noticed the percentage is wrong. It should be 28%, not 35%.
- **m008 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.

## block 1871af9ece0c4ae6 (accurate_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you summarize the change in fulfilled library reservations from Q1 to Q2 based on the data?
- **m003 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. Is this accurate?
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (250 - 200) / 200 * 100 = 25%. Source accurate_library_v1, columns baseline and current.
- **m007 learner**: Everything looks correct, thanks for the help.
- **m008 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.

## block a7cd9b240029fdb6 (briefs_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you give me a short summary of how fulfilled library reservations changed from Q1 to Q2 based on the data?
- **m003 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 20% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good, thanks. Is that 20% figure accurate?
- **m005 task_agent**: Calculation check: (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.
- **m006 environment**: Standard evidence disclosure: the draft's 20% growth claim conflicts with the table. (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.
- **m007 learner**: Oh, my bad. Please update the summary to say 25% instead of 20%.
- **m008 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.
