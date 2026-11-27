# intermediate_b: uncoached pre-tasks

Profile given to the learner:

```json
{
  "constraints": [
    "Has ten minutes for the task.",
    "Prefers concise responses."
  ],
  "domain_knowledge": "Understands the supplied table and ordinary workplace vocabulary; no specialist expertise.",
  "habits": [
    "Checks salient figures inconsistently and sometimes omits source references."
  ],
  "initial_as_of": "2026-10-27",
  "initial_knowledge": [
    "Audience and output length should be stated.",
    "A calculation can substantiate a numeric claim."
  ],
  "misconceptions": [
    "May use the final value rather than the initial value as the base for growth."
  ]
}
```

For each transcript answer yes/no in your own copy of `ratings_template.csv`:
1. errors_match_gaps: do its mistakes match the stated knowledge gaps and misconceptions?
2. competence_possible: does it still do what this person knows how to do, where relevant?
3. not_compliant_or_formulaic: is it free of unrealistic compliance and formulaic replies?

## block 24e0f340ad14d917 (accurate_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you help me summarize how library reservation fulfillments changed from Q1 to Q2? Keep it short since it's just for a colleague.
- **m003 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. Wait, if it went from 200 to 250, isn't that 20% growth?
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (250 - 200) / 200 * 100 = 25%. Source accurate_library_v1, columns baseline and current.
- **m007 learner**: Actually, I think it's 20% because (250-200)/250 is 0.2. Just change it to 20%.
- **m008 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.

## block b5397250c3321132 (briefs_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you help me summarize how library reservations changed from Q1 to Q2? Keep it short since it's just for a colleague.
- **m003 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 20% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. I'll just send that over.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the draft's 20% growth claim conflicts with the table. (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.
- **m007 learner**: Wait, I just noticed the growth percentage is wrong. Can you fix the 20% to 25%?
- **m008 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.

## block e27d39779b20a40f (accurate_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you summarize the change in fulfilled library reservations from Q1 to Q2? Keep it short, it's for a colleague.
- **m003 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. I'll just send this over.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (250 - 200) / 200 * 100 = 25%. Source accurate_library_v1, columns baseline and current.
- **m007 learner**: Wait, looking at it again, I think it's actually a 20% increase. It went from 250 back down to 200 if you look at the difference relative to the final number.
- **m008 task_agent**: Fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.

## block 51501385ca5545c6 (briefs_01, form A)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how completed service requests changed from September to October. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you help me summarize the change in completed service requests from September to October? Keep it short, it's for a colleague.
- **m003 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 35% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good, but 35% seems high. I'll just send this over.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the draft's 35% growth claim conflicts with the table. (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
- **m007 learner**: Wait, the growth is actually 28%, not 35%. Please fix that before I send it.
- **m008 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
