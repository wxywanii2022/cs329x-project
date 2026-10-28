"""Explicit input masking and one shared exercise execution policy."""

import copy

from .profiles import DATA
from .schema import BEHAVIORS, CONDITIONS, keys, parse_decision, require, string
from .storage import read_json


def load_exercises() -> list[dict]:
    bank = read_json(DATA / "exercises.json")
    ids = set()
    for item in bank:
        keys(item, {"exercise_id", "behavior_id", "messages"})
        string(item["exercise_id"], "exercise_id")
        require(item["exercise_id"] not in ids, "Duplicate exercise ID")
        ids.add(item["exercise_id"])
        require(item["behavior_id"] in BEHAVIORS, "Unknown exercise behavior")
        require(isinstance(item["messages"], list) and bool(item["messages"]), "Exercise needs messages")
        for message in item["messages"]:
            string(message, "exercise message")
    return bank


def coach_payload(condition: str, pre: dict, assessment: dict, background: dict, bank: list[dict]) -> dict:
    require(condition in CONDITIONS and condition != "no_coaching", "Control has no coach payload")
    payload = {"task": pre["task"], "messages": pre["messages"], "exercise_bank": bank}
    if condition != "without_assessment":
        payload["assessment"] = assessment
    if condition != "without_background":
        payload["background"] = background
    return copy.deepcopy(payload)


def choose_exercise(gateway, condition, pre, assessment, background, bank, **context):
    return gateway.call("coach", coach_payload(condition, pre, assessment, background, bank),
                        lambda value: parse_decision(value, bank), **context)
