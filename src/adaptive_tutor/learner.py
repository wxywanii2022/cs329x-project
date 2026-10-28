"""Condition-blind learner routing; no skill counters or hidden memory updates."""

import copy

from .schema import parse_utterance


def learner_payload(state: dict, task: dict, stage: str) -> dict:
    return {"initial_background": copy.deepcopy(state["background"]),
            "observed_history": [{"actor": m["actor"], "content": m["content"]} for m in state["messages"]],
            "task": copy.deepcopy(task), "stage": stage}


def learner_turn(gateway, state: dict, task: dict, stage: str, **context):
    return gateway.call("learner", learner_payload(state, task, stage), parse_utterance, **context)
