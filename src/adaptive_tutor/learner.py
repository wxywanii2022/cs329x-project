"""Condition-blind learner routing; no skill counters or hidden memory updates."""

import copy

from .profiles import DATA
from .schema import parse_utterance

# v2 after pilot 1: experts acted much like novices (the v1 prompt never said to act on
# the profile's knowledge and habits), and no learner declined practice (v1 never named
# the runner's decline phrase). v1 stays for reproducing outputs/rq2-pilot.
LEARNER_PROMPT = DATA.parent / "prompts" / "learner_v2.txt"


def learner_payload(state: dict, task: dict, stage: str) -> dict:
    return {"initial_background": copy.deepcopy(state["background"]),
            "observed_history": [{"actor": m["actor"], "content": m["content"]} for m in state["messages"]],
            "task": copy.deepcopy(task), "stage": stage}


def learner_turn(gateway, state: dict, task: dict, stage: str, **context):
    return gateway.call("learner", learner_payload(state, task, stage), parse_utterance,
                        prompt_text=LEARNER_PROMPT.read_text(encoding="utf-8"), prompt_version=LEARNER_PROMPT.stem,
                        **context)
