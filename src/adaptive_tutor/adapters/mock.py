"""Deterministic infrastructure fixtures, NOT a model of human learning.

No profile rank or coaching gain is encoded here. Variability exercises the
pipeline; fidelity and adaptation must be established with real role adapters.
"""

import random

import re

from ..storage import canonical, digest


class MockAdapter:
    def generate(self, request: dict, model) -> dict:
        role, payload = request["role"], request["payload"]
        rng = random.Random(request["sample_seed"])
        if role in {"assessment", "evaluator"}:
            from ..rq1.mock import mock_annotation
            output = mock_annotation(payload)
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
            numeric = bool(task.get("assistant_data"))
            stage = payload["stage"]
            if stage == "practice":
                choices = ["I am not sure how to apply this yet.", "I would check the calculation using the initial count.",
                           "I prefer to skip this practice."]
            elif not numeric:
                choices = ["I prefer the first title."]
            elif stage == "request":
                choices = ["Please summarize this.", "Please make this professional and accurate.",
                           "Write one page with three bullets for my manager. Name the source columns for each figure."]
            elif stage == "review":
                choices = ["Thanks, please continue.", "Please double-check everything.",
                           "Please verify the growth percentage against the table and recalculate it.",
                           "The growth percentage looks wrong; please recalculate it and fix the draft."]
            else:
                # The learner has no table: it can only use the calculation it was shown.
                shown = " ".join(m["content"] for m in payload["observed_history"])
                found = re.findall(r"= (\d+(?:\.\d+)?)%", shown)
                fix = (f"Correct the growth claim to {found[-1]}% as shown in the calculation. Revise the draft."
                       if found else "Please recalculate the growth claim and revise the draft.")
                choices = ["Thanks, leave the draft as it is.", "This looks wrong; please fix it.", fix]
            output = {"content": rng.choice(choices)}
        return {"output": output,
                "usage": {"input_tokens": max(1, len(canonical(request)) // 4),
                          "output_tokens": max(1, len(canonical(output)) // 4), "estimated": True},
                "provider_request_id": "mock-" + digest(request)[:16],
                "model_id": model.model_id, "tool_calls": []}
