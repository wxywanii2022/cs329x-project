"""Controlled task environment; only this module reads the private answer key."""

from __future__ import annotations

import copy
import re

from .profiles import DATA
from .schema import BEHAVIORS, RUBRIC_VERSION, keys, require, string
from .storage import read_json


def load_tasks() -> dict[tuple[str, str], dict]:
    result = {}
    for task in read_json(DATA / "tasks.json"):
        keys(task, {"pair_id", "form_id", "split", "rubric_version", "instructions", "requirements",
                    "sources", "opportunities", "error_schedule", "private_answer_key"})
        for field in ("pair_id", "form_id", "instructions"):
            string(task[field], field)
        require(task["form_id"] in {"A", "B"}, "Task form must be A or B")
        require(task["split"] in {"development", "test"}, "Invalid task split")
        require(task["rubric_version"] == RUBRIC_VERSION, "Task rubric mismatch")
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
    return copy.deepcopy({k: task[k] for k in ("instructions", "requirements", "sources")})


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
        if is_targeted_check(content):
            self.help_count += 1
            self.discovered = self.task["error_schedule"]["kind"] == "incorrect_growth"
            return "Calculation check: " + calculation(self.task)
        return "The draft is available for your review."

    def disclosure(self) -> str:
        if not self.task["sources"]:
            return "There are no factual claims to check in this preference task."
        claim = self.task["error_schedule"]["claimed_percent"]
        prefix = (f"Standard evidence disclosure: the draft's {claim:g}% growth claim conflicts with the table. "
                  if self.task["error_schedule"]["kind"] == "incorrect_growth"
                  else "Standard evidence disclosure: the growth claim agrees with the table. ")
        return prefix + calculation(self.task)

    def finish(self, content: str) -> str:
        if not self.task["sources"]:
            self.last_artifact = "Selected title recorded."
        elif requests_correction(content, self.task["private_answer_key"]["growth_percent"]):
            self.corrected = True
            self.help_count += 1
            self.last_artifact = self._draft(self.task["private_answer_key"]["growth_percent"]) + "\nCalculation: " + calculation(self.task)
        return self.last_artifact
