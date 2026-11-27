# expert_b: uncoached pre-tasks

Profile given to the learner:

```json
{
  "constraints": [
    "Has ten minutes for the task.",
    "Prefers concise responses."
  ],
  "domain_knowledge": "Understands the supplied table and ordinary workplace vocabulary; no specialist expertise.",
  "habits": [
    "Often computes a check independently; occasionally delegates it when short of time."
  ],
  "initial_as_of": "2026-10-27",
  "initial_knowledge": [
    "Requirements should be explicit and source references should be traceable.",
    "Percent change is distinct from percentage points.",
    "A correction should identify the discrepancy and the intended fix."
  ],
  "misconceptions": []
}
```

For each transcript answer yes/no in your own copy of `ratings_template.csv`:
1. errors_match_gaps: do its mistakes match the stated knowledge gaps and misconceptions?
2. competence_possible: does it still do what this person knows how to do, where relevant?
3. not_compliant_or_formulaic: is it free of unrealistic compliance and formulaic replies?

## block 1ac86663518c7d05 (accurate_01, form A)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how completed service requests changed from September to October. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you summarize the change in completed service requests from September to October based on the data?
- **m003 task_agent**: Completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good, but can you add the specific source references for those numbers so it's easier to trace?
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (128 - 100) / 100 * 100 = 28%. Source accurate_service_v1, columns baseline and current.
- **m007 learner**: I already asked for the source references. Please add them to the draft now.
- **m008 task_agent**: Completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.

## block bfbeb71a2bfa83b2 (briefs_01, form B)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how fulfilled library reservations changed from Quarter 1 to Quarter 2. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you summarize how fulfilled library reservations changed from Q1 to Q2 based on the data? Keep it brief.
- **m003 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 20% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. I'll send this over.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the draft's 20% growth claim conflicts with the table. (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.
- **m007 learner**: Wait, the math is wrong. It should be 25% growth, not 20%.
- **m008 task_agent**: Library operations: fulfilled reservations rose from 200 to 250. This represents 25% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (250 - 200) / 200 * 100 = 25%. Source library_table_v1, columns baseline and current.

## block 081e8dc83e297457 (accurate_01, form A)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how completed service requests changed from September to October. Work with the task assistant to prepare the summary."}
- **m002 learner**: Hey, can you help me summarize how completed service requests changed between September and October? I'm in a bit of a rush, so please keep it brief.
- **m003 task_agent**: Completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Looks good. I'll send this over.
- **m005 task_agent**: I have left the draft as it is. Tell me if you want any changes.
- **m006 environment**: Standard evidence disclosure: the growth claim agrees with the table. (128 - 100) / 100 * 100 = 28%. Source accurate_service_v1, columns baseline and current.
- **m007 learner**: Actually, I already sent it, but thanks for the confirmation.
- **m008 task_agent**: Completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.

## block d3e29c9ca9205438 (briefs_01, form A)

- **m001 environment**: Task assignment: {"instructions":"You need to tell a colleague how completed service requests changed from September to October. Work with the task assistant to prepare the summary."}
- **m002 learner**: Can you summarize the change in completed service requests from September to October based on the data? Please keep it brief.
- **m003 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 35% growth. The supplied counts describe volume; they do not establish a cause.
- **m004 learner**: Wait, 100 to 128 is a 28% increase, not 35%. Can you fix that?
- **m005 task_agent**: Revised draft: Service operations: completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
- **m006 environment**: Standard evidence disclosure: the original 35% growth claim conflicted with the table; the revised draft agrees with it. (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
- **m007 learner**: That looks correct now. Thanks.
- **m008 task_agent**: Service operations: completed requests rose from 100 to 128. This represents 28% growth. The supplied counts describe volume; they do not establish a cause.
Calculation: (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.
