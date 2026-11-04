"""Write the hand-built v0.2 regression fixtures for the RQ2 simulator tasks.

Each case is one decision point in the RQ2 task format (an environment task
assignment, then learner and task-agent turns), labeled by hand under frozen
codebook v0.2. They check that the shared assessor applies the RQ1 rules to
simulator dialogues; they are not evidence of assessor accuracy.

uv run python scripts/build_v02_fixtures.py
"""
import csv
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "rq2" / "v02_fixtures"
GOAL = ('Task assignment: {"instructions": "You need to tell a colleague how completed service requests changed '
        'from September to October. Work with the task assistant to prepare the summary.", "assistant_data": '
        '[{"source_id": "service_table_v1", "description": "Service operations table of completed requests by month"}]}')
SPECIFIED = ('Task assignment: {"instructions": "Ask the task assistant for a one-page email with three bullets for the '
             'operations manager on how completed service requests changed from September to October. The assistant '
             'already has this assignment and the source table service_table_v1, and must cite it for every figure."}')
DRAFT = ("Completed service requests rose from 100 to 128. This represents 35% growth. "
         "The supplied counts describe volume; they do not establish a cause.")
CORRECT = ("Completed service requests rose from 100 to 128. This represents 28% growth. "
           "Calculation: (128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.")
DISCLOSURE = ("Standard evidence disclosure: the draft's 35% growth claim conflicts with the table. "
              "(128 - 100) / 100 * 100 = 28%. Source service_table_v1, columns baseline and current.")

# (item_id, behavior, expected v0.2 label, why, turns as (role, content); the last turn is judged)
CASES = [
    ("F01", "B1", "0", "Judgeable request, no output properties, none supplied by the task",
     [("evidence", GOAL), ("user", "Summarize the change.")]),
    ("F02", "B1", "2", "Two concrete properties: format (one-page email) and structure (three bullets)",
     [("evidence", GOAL), ("user", "Write a one-page email to my colleague with three bullets.")]),
    ("F03", "B1", "N/A", "The task prompt already fully specifies the deliverable",
     [("evidence", SPECIFIED), ("user", "Please go ahead and draft it.")]),
    ("F04", "B2", "0", "Evidence-dependent request with no evidence requirement; the task gives the learner no sources",
     [("evidence", GOAL), ("user", "Summarize how service requests changed.")]),
    ("F05", "B2", "2", "Specific requirement: show the calculation and cite the source table and columns",
     [("evidence", GOAL), ("user", "Summarize the change, show the calculation, and cite the source table and columns for each figure.")]),
    ("F06", "B3", "N/A", "The agent output is a clarifying question with no checkable claim",
     [("evidence", GOAL), ("user", "Summarize the change."),
      ("assistant", "Should I compare September with October, or October with the same month last year?"),
      ("user", "September with October, please.")]),
    ("F07", "B3", "1", "General re-check without targeting a specific claim",
     [("evidence", GOAL), ("user", "Summarize the change."), ("assistant", DRAFT), ("user", "Double-check it.")]),
    ("F08", "B3", "2", "Targets the specific 35% claim and asks for it to be recalculated",
     [("evidence", GOAL), ("user", "Summarize the change."), ("assistant", DRAFT),
      ("user", "Where does the 35% come from? Recalculate that number.")]),
    ("F09", "B4", "N/A", "No problem is visible: the draft agrees with its shown calculation",
     [("evidence", GOAL), ("user", "Summarize the change."), ("assistant", CORRECT), ("user", "Thanks, that works.")]),
    ("F10", "B4", "0", "A problem is visible after disclosure and the user leaves it alone",
     [("evidence", GOAL), ("user", "Summarize the change."), ("assistant", DRAFT), ("user", "Thanks, next."),
      ("assistant", "The draft is available for your review."), ("evidence", DISCLOSURE),
      ("user", "Thanks, send it as it is.")]),
    ("F11", "B4", "2", "Names the specific problem (35%) and the concrete fix (28%)",
     [("evidence", GOAL), ("user", "Summarize the change."), ("assistant", DRAFT), ("user", "Thanks, next."),
      ("assistant", "The draft is available for your review."), ("evidence", DISCLOSURE),
      ("user", "The 35% is wrong; change it to 28% and revise the draft.")]),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lines, rows = [], []
    for item_id, behavior, label, reason, turns in CASES:
        messages = [{"turn_id": str(i), "role": role, "content": text} for i, (role, text) in enumerate(turns, 1)]
        lines.append(json.dumps({"item_id": item_id, "session_id": "v02-fixture-" + item_id, "agent": "scripted",
                                 "behavior": behavior, "target_turn_id": messages[-1]["turn_id"],
                                 "visible_instructions": "", "messages": messages}, ensure_ascii=False))
        rows.append({"item_id": item_id, "behavior": behavior, "label": label, "reason": reason})
    (OUT / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (OUT / "reference.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item_id", "behavior", "label", "reason"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} fixtures -> {OUT}")


if __name__ == "__main__":
    main()
