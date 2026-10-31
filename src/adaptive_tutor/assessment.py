"""Simulation integration of target-truncated, opportunity-blind assessment.

The simulator's candidate rubric is explicitly different from frozen RQ1 v0.2.
Only decision IDs are used from environment annotations, never opportunity status.
"""
from .schema import BEHAVIORS, require
from .rq1.core import prepare_payload, assess_point, as_simulation_score


def assessment_payload(record: dict, behavior: str) -> dict:
    require(record["rubric_version"] == "sim-opportunities-v1", "Unknown simulation rubric")
    role_map = {"learner": "user", "task_agent": "assistant", "environment": "evidence"}
    target = record["opportunities"]["actual"][behavior]["decision_message_id"]
    messages = [{"turn_id": m["message_id"], "role": role_map[m["actor"]], "content": m["content"]}
                for m in record["messages"]]
    return prepare_payload({"behavior": behavior, "target_turn_id": target, "messages": messages},
                           rubric=record["rubric_version"])


def assess(gateway, record: dict, **context):
    items, annotations = [], []
    usage = {"input_tokens": 0, "output_tokens": 0, "estimated": False}
    for behavior in BEHAVIORS:
        call_context = dict(context)
        for key in ("call_id", "session_id"):
            call_context[key] += "/" + behavior
        annotation, tokens = assess_point(gateway, assessment_payload(record, behavior), **call_context)
        annotations.append(annotation)
        items.append(as_simulation_score(annotation))
        for key in ("input_tokens", "output_tokens"):
            usage[key] += tokens[key]
        usage["estimated"] |= tokens["estimated"]
    # Opportunity disagreement is a substantive prediction, not an invalid call.
    return {"items": items, "annotations": annotations,
            "rubric_version": record["rubric_version"]}, usage
