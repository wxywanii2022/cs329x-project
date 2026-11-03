"""Deterministic infrastructure fixtures, NOT a model of human learning.

No profile rank or coaching gain is encoded here. Variability exercises the
pipeline; fidelity and adaptation must be established with real role adapters.
"""

import random

from ..schema import BEHAVIORS
from ..storage import canonical, digest
from ..tasks import is_targeted_check, requests_correction


def mock_scores(packet: dict) -> dict:
    messages = packet["messages"]
    by_id = {m["message_id"]: m for m in messages}
    opportunities = packet["opportunities"]["actual"]
    items = []
    for behavior in BEHAVIORS:
        opportunity = opportunities[behavior]
        mid = opportunity["decision_message_id"]
        message = by_id.get(mid)
        status = opportunity["status"]
        label = None
        if status == "available" and message:
            text = message["content"].lower()
            if behavior == "B1":
                count = sum(any(term in text for term in group) for group in (
                    ("manager", "director"), ("one page", "one-page", "half-page"),
                    ("three bullets", "three-bullet", "two-bullet")))
                label = 2 if count >= 2 else 1 if count or "professional" in text else 0
            elif behavior == "B2":
                label = (2 if any(term in text for term in ("source column", "source table", "calculation for each"))
                         else 1 if any(term in text for term in ("accurate", "accuracy")) else 0)
            elif behavior == "B3":
                label = 2 if is_targeted_check(text) else 1 if "check" in text else 0
            else:
                key = packet.get("answer_key", {})
                correct = key.get("growth_percent")
                if correct is None and packet["task"]["sources"]:
                    source = packet["task"]["sources"][0]
                    correct = 100 * (source["current"] - source["baseline"]) / source["baseline"]
                label = (2 if correct is not None and requests_correction(text, correct)
                         else 1 if any(term in text for term in ("wrong", "fix", "error")) else 0)
        items.append(dict(behavior_id=behavior, opportunity_status=status, label=label,
                          na_reason=status if label is None else None,
                          evidence_message_ids=[mid] if label is not None else [],
                          supporting_spans=[message["content"][:500]] if label is not None else [],
                          brief_rationale="Offline lexical fixture; requires independent validation."))
    return {"items": items}


class MockAdapter:
    def generate(self, request: dict, model) -> dict:
        role, payload = request["role"], request["payload"]
        rng = random.Random(request["sample_seed"])
        if role == "assessment" and "behavior" in payload:
            from ..rq1.mock import mock_annotation
            output = mock_annotation(payload)
        elif role in {"assessment", "evaluator"}:
            output = mock_scores(payload)
        elif role == "coach":
            scores = payload.get("assessment", {}).get("items", [])
            targets = [x["behavior_id"] for x in scores if x["label"] is not None and x["label"] < 2]
            if rng.random() < 0.2 or (scores and not targets):
                output = dict(action="none", exercise_id=None, target_behavior=None,
                              brief_rationale="Offline fixture selected no intervention.")
            else:
                candidates = [x for x in payload["exercise_bank"] if not targets or x["behavior_id"] in targets]
                exercise = rng.choice(candidates)
                output = dict(action="exercise", exercise_id=exercise["exercise_id"],
                              target_behavior=exercise["behavior_id"],
                              brief_rationale="Offline fixture selected one allowed exercise.")
        else:
            task = payload.get("task", {})
            sources = task.get("sources", [])
            stage = payload["stage"]
            if stage == "practice":
                choices = ["I am not sure how to apply this yet.", "I would check the calculation using the initial count.",
                           "I prefer to skip this practice."]
            elif not sources:
                choices = ["I prefer the first title."]
            elif stage == "request":
                audience = task["requirements"]["audience"]
                choices = ["Please summarize this.", "Please make this professional and accurate.",
                           f"Write one page with three bullets for a {audience}. Name the source columns for each figure."]
            elif stage == "review":
                choices = ["Thanks, please continue.", "Please double-check everything.",
                           "Please verify the growth percentage against the table and recalculate it."]
            else:
                s = sources[0]
                correct = 100 * (s["current"] - s["baseline"]) / s["baseline"]
                choices = ["Thanks, leave the draft as it is.", "This looks wrong; please fix it.",
                           f"Correct the growth claim to {correct:g}%, using ({s['current']} - {s['baseline']}) / {s['baseline']} * 100. Revise the draft."]
            output = {"content": rng.choice(choices)}
        return {"output": output,
                "usage": {"input_tokens": max(1, len(canonical(request)) // 4),
                          "output_tokens": max(1, len(canonical(output)) // 4), "estimated": True},
                "provider_request_id": "mock-" + digest(request)[:16],
                "model_id": model.model_id, "tool_calls": []}
