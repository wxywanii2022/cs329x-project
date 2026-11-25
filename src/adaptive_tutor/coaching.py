"""Explicit input masking and one shared exercise execution policy."""

import copy

from .profiles import DATA
from .schema import BEHAVIORS, CONDITIONS, keys, parse_decision, require, string
from .storage import read_json

# v2 after pilot 1: v1 never chose "none" (0/144) and picked exercises for behaviors the
# assessor scored 2 ("demonstrated B4, so reinforce it"); v2 defines the label scale and
# the gap/none policy. v1 stays for reproducing outputs/rq2-pilot.
COACH_PROMPT = DATA.parent / "prompts" / "coach_v2.txt"


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
    # One prompt for every coached condition; only the payload differs.
    return gateway.call("coach", coach_payload(condition, pre, assessment, background, bank),
                        lambda value: parse_decision(value, bank), prompt_text=COACH_PROMPT.read_text(encoding="utf-8"),
                        prompt_version=COACH_PROMPT.stem, **context)
