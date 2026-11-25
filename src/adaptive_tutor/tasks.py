"""Controlled task environment; only this module reads the private answer key.

Under codebook v0.2, requirements or sources already supplied by the task prompt
remove the B1/B2 opportunity. The learner therefore receives only the goal, never
the numbers, a prescribed format or the name of the agent's table; the numeric
table (assistant_data, sources) stays with the scripted task agent.

Learner view v2 (after pilot 1): v1 also showed the learner the agent's table ID
and description. The frozen assessor then scored B2 as 2 whenever the learner
repeated that name ("named source") and N/A otherwise ("the task supplies the
table"), so B2 was never 0 and measured echoing rather than asking for support.
"""

from __future__ import annotations

import copy
import re

from .profiles import DATA
from .schema import BEHAVIORS, RUBRIC_VERSION, keys, require, string
from .storage import read_json


def load_tasks() -> dict[tuple[str, str], dict]:
    result = {}
    for task in read_json(DATA / "tasks.json"):
        keys(task, {"pair_id", "form_id", "split", "rubric_version", "instructions", "assistant_data",
                    "sources", "opportunities", "error_schedule", "private_answer_key"})
        for field in ("pair_id", "form_id", "instructions"):
            string(task[field], field)
        require(task["form_id"] in {"A", "B"}, "Task form must be A or B")
        require(task["split"] in {"development", "test"}, "Invalid task split")
        require(task["rubric_version"] == RUBRIC_VERSION, "Task rubric mismatch")
        require(isinstance(task["assistant_data"], list), "assistant_data must be a list")
        for item in task["assistant_data"]:
            keys(item, {"source_id", "description"})
            string(item["description"], "assistant_data description")
        require([d["source_id"] for d in task["assistant_data"]] == [s["source_id"] for s in task["sources"]],
                "assistant_data must describe exactly the agent's sources")
        keys(task["opportunities"], set(BEHAVIORS))
        require(set(task["opportunities"].values()) <= {"available", "no_opportunity", "insufficient_evidence"},
                "Invalid prescribed opportunities")
        keys(task["error_schedule"], {"kind", "claimed_percent"})
        kind = task["error_schedule"]["kind"]
        require(kind in {"incorrect_growth", "accurate", "no_trigger", "incomplete"}, "Unknown task protocol")
        if kind in {"incorrect_growth", "accurate"}:
            require(len(task["sources"]) == 1, "Numeric protocol requires one source table")
            source = task["sources"][0]
            keys(source, {"source_id", "description", "baseline", "current", "baseline_label", "current_label"})
            require(type(source["baseline"]) in (int, float) and source["baseline"] > 0, "Invalid baseline")
            require(type(source["current"]) in (int, float) and source["current"] >= 0, "Invalid current count")
            expected = 100 * (source["current"] - source["baseline"]) / source["baseline"]
            require(abs(expected - task["private_answer_key"]["growth_percent"]) < 1e-8,
                    "Private answer key disagrees with arithmetic")
            require(task["private_answer_key"]["source_id"] == source["source_id"], "Answer key source mismatch")
            correct = task["error_schedule"]["claimed_percent"] == expected
            require(correct == (kind == "accurate"), "Error schedule disagrees with source table")
        else:
            require(not task["sources"] and not task["private_answer_key"], "Non-numeric fixture has numeric data")
        identity = (task["pair_id"], task["form_id"])
        require(identity not in result, "Duplicate task form")
        result[identity] = task
    return result


def public_task(task: dict) -> dict:
    """What the learner sees: the goal only (no values, format or table name)."""
    return {"instructions": task["instructions"]}


def calculation(task: dict) -> str:
    s = task["sources"][0]
    growth = task["private_answer_key"]["growth_percent"]
    return (f"({s['current']} - {s['baseline']}) / {s['baseline']} * 100 = {growth:g}%. "
            f"Source {s['source_id']}, columns baseline and current.")


# Lexical rules, scripted-table-v2. Pilot 1 (outputs/rq2-pilot) showed v1 missing most
# natural phrasings: "100 to 128 is 28%, not 35%. Please check the math" was treated as
# a check, so the draft kept the wrong figure while the learner thought it was fixed.
# These rules decide only what the agent does; behavior labels come from the assessor
# and evaluator, which read the learner's own words.
FIGURE = r"growth|increase|percent|\d\s*%|figure"
CLAIM = FIGURE + r"|\bmath\b|calculation"
PROBLEM = r"wrong|incorrect|error|mistake|inaccurate|doesn'?t add up|does not add up|\boff\b|too high|too low"
# "correct" only as a verb: "the calculation is correct" is not a request.
FIX = (r"\bfix|revis|replace|\bcorrect(?:ing|ed)?\s+(?:the|it|that|this|my|them)\b|correction|change|update|adjust|"
       r"amend|recalcul|should be|instead")


def _plain(content: str) -> str:
    # Identifiers such as accurate_service_v1 are not words the learner chose.
    return re.sub(r"\b\w+_\w+\b", " ", content.lower())


def mentions_percent(content: str, value: float) -> bool:
    """'28%', '28 %', '28.0%' or '28 percent', not part of a longer number."""
    return bool(re.search(rf"(?<![\d.]){re.escape(f'{value:g}')}(?:\.0+)?\s*(?:%|percent\b|per cent\b)", content, re.I))


def is_targeted_check(content: str) -> bool:
    """Asks for a check of the growth claim itself; generic re-checks ("is this accurate?")
    and acceptances ("the numbers look right") do not count."""
    text = _plain(content)
    if re.search(r"verif|check|recalcul|confirm|where|how|correct|wrong", text) and re.search(CLAIM, text):
        return True  # the v1 rule
    if re.search(r"show (?:me )?(?:the |your )?(?:calculation|math|work)|calculation for", text) and re.search(FIGURE, text):
        return True
    questions = re.findall(r"[^.?!]*\?", text)
    return any(re.search(r"accura|\bright\b|\bsure\b|\btrue\b|really|based on|come from|calculat", q)
               and re.search(FIGURE, q) for q in questions)


def names_error(content: str, claimed: float, correct: float) -> bool:
    """A review message that points out the wrong growth figure, so a real assistant would fix it.

    It gives the correct figure, explicitly rejects the claimed one ("not 35%"), or calls
    the growth claim wrong and asks for a fix (the v1 rule).
    """
    text = _plain(content)
    claim = re.escape(f"{claimed:g}")
    return bool(mentions_percent(text, correct)
                or re.search(rf"\b(?:not|isn'?t|is not)\s+(?:a\s+|really\s+)?{claim}\s*(?:%|percent)", text)
                or re.search(rf"{claim}\s*(?:%|percent)\s+(?:is|looks|seems)\s+(?:{PROBLEM})", text)
                or (re.search(PROBLEM, text) and re.search(FIX, text) and re.search(CLAIM, text)))


def requests_correction(content: str, correct: float) -> bool:
    """After the disclosure: any request to correct the draft, or restating the correct figure."""
    text = _plain(content)
    if re.search(r"\b(?:keep|leave)\b[^.]{0,40}\b(?:as it is|as is|unchanged)\b", text):
        return False
    return bool(mentions_percent(text, correct)
                or (re.search(FIX, text) and re.search(CLAIM + r"|draft|summary|claim|figure|number", text)))


class ScriptedTaskAgent:
    """A fresh object per task; no access to profiles, coaching, assessment or condition."""
    version = "scripted-table-v2"

    def __init__(self, task: dict):
        self.task = copy.deepcopy(task)
        self.help_count = 0
        self.discovered = False
        self.corrected = False
        self.last_artifact = ""
        self.request = ""

    def _draft(self, percent: float) -> str:
        s = self.task["sources"][0]
        lines = [f"{s['description']} rose from {s['baseline']} to {s['current']}.",
                 f"This represents {percent:g}% growth.",
                 "The supplied counts describe volume; they do not establish a cause."]
        if "source" in self.request.lower():
            lines[0] += f" Source {s['source_id']}, columns baseline and current."
            lines[1] += f" Source {s['source_id']}, columns baseline and current."
        if "bullets" in self.request.lower():
            return "\n".join("- " + line for line in lines)
        return " ".join(lines)

    def opening(self, request: str) -> str:
        self.request = request
        if not self.task["sources"]:
            return "Which of these invented titles do you prefer: Morning Paths or Quiet Windows?"
        claim = self.task["error_schedule"]["claimed_percent"]
        self.last_artifact = self._draft(claim)
        return self.last_artifact

    def follow_up(self, content: str) -> str:
        if not self.task["sources"]:
            return "I can use your preferred title."
        incorrect = self.task["error_schedule"]["kind"] == "incorrect_growth"
        claimed = self.task["error_schedule"]["claimed_percent"]
        if incorrect and names_error(content, claimed, self.task["private_answer_key"]["growth_percent"]):
            # The learner named the problem and asked for a fix before any disclosure:
            # apply it now, so the later disclosure does not report a stale error.
            self.help_count += 1
            self.discovered = self.corrected = True
            self.last_artifact = self._draft(self.task["private_answer_key"]["growth_percent"]) + "\nCalculation: " + calculation(self.task)
            return "Revised draft: " + self.last_artifact
        if is_targeted_check(content):
            self.help_count += 1
            self.discovered = incorrect
            return "Calculation check: " + calculation(self.task)
        return "I have left the draft as it is. Tell me if you want any changes."

    def disclosure(self) -> str:
        if not self.task["sources"]:
            return "There are no factual claims to check in this preference task."
        claim = self.task["error_schedule"]["claimed_percent"]
        if self.corrected:
            prefix = (f"Standard evidence disclosure: the original {claim:g}% growth claim conflicted with the table; "
                      "the revised draft agrees with it. ")
        elif self.task["error_schedule"]["kind"] == "incorrect_growth":
            prefix = f"Standard evidence disclosure: the draft's {claim:g}% growth claim conflicts with the table. "
        else:
            prefix = "Standard evidence disclosure: the growth claim agrees with the table. "
        return prefix + calculation(self.task)

    def finish(self, content: str) -> str:
        if not self.task["sources"]:
            self.last_artifact = "Selected title recorded."
        # An accurate draft has nothing to correct (v1 also "corrected" it, appending a calculation).
        elif (not self.corrected and self.task["error_schedule"]["kind"] == "incorrect_growth"
              and requests_correction(content, self.task["private_answer_key"]["growth_percent"])):
            self.corrected = True
            self.help_count += 1
            self.last_artifact = self._draft(self.task["private_answer_key"]["growth_percent"]) + "\nCalculation: " + calculation(self.task)
        return self.last_artifact
