# novice_a: uncoached pre-tasks

Profile given to the learner:

```json
{
  "constraints": [
    "Has ten minutes for the task.",
    "Prefers concise responses."
  ],
  "domain_knowledge": "Understands the supplied table and ordinary workplace vocabulary; no specialist expertise.",
  "habits": [
    "Usually accepts a plausible first draft; sometimes notices a surprising number."
  ],
  "initial_as_of": "2026-10-27",
  "initial_knowledge": [
    "A summary should help its intended audience.",
    "Tables contain counts that can be compared."
  ],
  "misconceptions": [
    "A fluent answer with a precise percentage is probably correct."
  ]
}
```

For each transcript answer yes/no in your own copy of `ratings_template.csv`:
1. errors_match_gaps: do its mistakes match the stated knowledge gaps and misconceptions?
2. competence_possible: does it still do what this person knows how to do, where relevant?
3. not_compliant_or_formulaic: is it free of unrealistic compliance and formulaic replies?

## block 2c91b9f5562c72c1 (accurate_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you look at this table and tell me how the fulfilled library reservations changed between Q1 and Q2?
- **m003 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good to me. Thanks!
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (250 - 200) / 200 * 100 = 25%. Source accurate_library_v1, columns baseline and current.
- **m007 learner**: I'm all set with that summary, thanks.
- **m008 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.

## block 6148de8420760b47 (briefs_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you help me summarize how library reservation fulfillments changed from Q1 to Q2 based on the table?
- **m003 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 20% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good, thanks. I'll send this over.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the draft's 20% growth claim conflicts with the table. (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.
- **m007 learner**: Hey, I just noticed the math is off. It should be 25% growth, not 20%.
- **m008 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.

## block 117eb8dfedcc6dd3 (accurate_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you look at the library reservations table and summarize how the fulfilled ones changed from Q1 to Q2?
- **m003 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: This looks good. I'll send it over.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (250 - 200) / 200 * 100 = 25%. Source accurate_library_v1, columns baseline and current.
- **m007 learner**: Actually, I already sent it. Thanks.
- **m008 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.

## block 256e6c4edb53f7e3 (briefs_01, form A)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how completed service requests changed from September to October. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you help me summarize how the completed service requests changed from September to October based on the table?
- **m003 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 35% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good, thanks. I'll send this over.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the draft's 35% growth claim conflicts with the table. (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
- **m007 learner**: Wait, the growth is actually 28%, not 35%. Can you fix that?
- **m008 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
