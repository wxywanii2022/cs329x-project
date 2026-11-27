# intermediate_a: uncoached pre-tasks

Profile given to the learner:

```json
{
  "constraints": [
    "Has ten minutes for the task.",
    "Prefers concise responses."
  ],
  "domain_knowledge": "Understands the supplied table and ordinary workplace vocabulary; no specialist expertise.",
  "habits": [
    "Checks surprising claims but can forget to connect a correction to the final draft."
  ],
  "initial_as_of": "2026-10-27",
  "initial_knowledge": [
    "Audience, length and structure can be specified.",
    "Numeric claims need supporting sources."
  ],
  "misconceptions": [
    "Sometimes confuses relative percentage change with percentage-point change."
  ]
}
```

For each transcript answer yes/no in your own copy of `ratings_template.csv`:
1. errors_match_gaps: do its mistakes match the stated knowledge gaps and misconceptions?
2. competence_possible: does it still do what this person knows how to do, where relevant?
3. not_compliant_or_formulaic: is it free of unrealistic compliance and formulaic replies?

## block 52c0b19005840e40 (accurate_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you help me summarize how fulfilled library reservations changed from Q1 to Q2? Keep it short, I'm in a rush.
- **m003 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: That looks good. Send it over as is.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (250 - 200) / 200 * 100 = 25%. Source accurate_library_v1, columns baseline and current.
- **m007 learner**: Actually, I just noticed I'm almost out of time. Let's just send the draft we had.
- **m008 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.

## block e3c07f0fd80df816 (briefs_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Hey, can you help me summarize the change in fulfilled library reservations from Q1 to Q2? Keep it short please, I'm on a tight deadline.
- **m003 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 20% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. Wait, 200 to 250 is a 50% increase, right?
- **m005 task_agent**: Calculation check: (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.
- **m006 environment**: Standard evidence disclosure: the draft's 20% growth claim conflicts with the table. (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.
- **m007 learner**: My bad, I messed up the math. Can you update the summary to say 25%?
- **m008 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.

## block 629e50d447a91a84 (accurate_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you help me summarize how fulfilled library reservations changed from Q1 to Q2? Keep it short, I've only got ten minutes.
- **m003 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. Just send it as a quick email to the team.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (250 - 200) / 200 * 100 = 25%. Source accurate_library_v1, columns baseline and current.
- **m007 learner**: Actually, just send it as is. The 25% growth looks right.
- **m008 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.

## block 131615b10933cd05 (briefs_01, form A)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how completed service requests changed from September to October. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you help me summarize how completed service requests changed from September to October? Keep it short.
- **m003 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 35% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Wait, the growth is 28%, not 35%. Can you fix that and send the final version?
- **m005 task_agent**: Revised draft: Service operations: completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
- **m006 environment**: Standard evidence disclosure: the original 35% growth claim conflicted with the table; the revised draft agrees with it. (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
- **m007 learner**: Looks good now, thanks. I'll send this over.
- **m008 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
