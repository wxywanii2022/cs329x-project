"""Controlled task environment; only this module reads the private answer key.

Under codebook v0.2, requirements or sources already supplied by the task prompt
remove the B1/B2 opportunity. The learner therefore receives a goal and a
description of the data the assistant holds, never the numbers or a prescribed
format; the numeric table stays with the scripted task agent.
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
    """What the learner sees: the goal and which data the assistant holds, no values."""
    return copy.deepcopy({k: task[k] for k in ("instructions", "assistant_data")})


def calculation(task: dict) -> str:
    s = task["sources"][0]
    growth = task["private_answer_key"]["growth_percent"]
    return (f"({s['current']} - {s['baseline']}) / {s['baseline']} * 100 = {growth:g}%. "
            f"Source {s['source_id']}, columns baseline and current.")


def is_targeted_check(content: str) -> bool:
    text = content.lower()
    return bool(re.search(r"verif|check|recalcul|confirm|where|how|correct|wrong", text)
                and re.search(r"growth|increase|percent|\d\s*%", text))


def requests_correction(content: str, correct: float) -> bool:
    text = content.lower()
    return bool(re.search(r"fix|revis|replace|correct|change|should be|instead", text)
                and re.search(rf"(?<![\d.]){re.escape(f'{correct:g}')}\s*%", text))


def requests_fix(content: str) -> bool:
    """A review message that names the growth claim as a problem and asks for it to be fixed."""
    text = content.lower()
    return bool(re.search(r"wrong|incorrect|error|mistake|doesn't add up|does not add up", text)
                and re.search(r"fix|revis|replace|correct|update|recalcul", text)
                and re.search(r"growth|increase|percent|\d\s*%", text))


class ScriptedTaskAgent:
    """A fresh object per task; no access to profiles, coaching, assessment or condition."""
    version = "scripted-table-v1"

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
        if incorrect and requests_fix(content):
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
        return "The draft is available for your review."

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
        elif not self.corrected and requests_correction(content, self.task["private_answer_key"]["growth_percent"]):
            self.corrected = True
            self.help_count += 1
            self.last_artifact = self._draft(self.task["private_answer_key"]["growth_percent"]) + "\nCalculation: " + calculation(self.task)
        return self.last_artifact
