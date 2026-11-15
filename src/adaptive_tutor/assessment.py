"""Simulation integration of target-truncated, opportunity-blind assessment.

Uses the same frozen v0.2 codebook, payload builder, output contract and quote
validator as RQ1. Only decision IDs are used from environment annotations,
never opportunity status.
"""
from .schema import ASSESSMENT_CONTRACT, BEHAVIORS, RUBRIC_VERSION, require
from .rq1.core import prepare_payload, assess_point, as_simulation_score


ROLE_MAP = {"learner": "user", "task_agent": "assistant", "environment": "evidence"}


def decision_payload(messages: list[dict], behavior: str, target: str | None, rubric: str) -> dict:
    """The RQ1 payload builder: one behavior, dialogue truncated at its decision turn."""
    require(rubric == RUBRIC_VERSION, "Record rubric differs from the frozen codebook")
    visible = [{"turn_id": m["message_id"], "role": ROLE_MAP[m["actor"]], "content": m["content"]}
               for m in messages] if target is not None else []
    return prepare_payload({"behavior": behavior, "target_turn_id": target, "messages": visible}, rubric=rubric)


def assessment_payload(record: dict, behavior: str) -> dict:
    target = record["opportunities"]["actual"][behavior]["decision_message_id"]
    return decision_payload(record["messages"], behavior, target, record["rubric_version"])


def assess(gateway, record: dict, **context):
    items, annotations = [], []
    usage = {"input_tokens": 0, "output_tokens": 0, "estimated": False}
    for behavior in BEHAVIORS:
        call_context = dict(context)
        for key in ("call_id", "session_id"):
            call_context[key] += "/" + behavior
        annotation, tokens = assess_point(gateway, assessment_payload(record, behavior),
                                          contract=ASSESSMENT_CONTRACT, **call_context)
        annotations.append(annotation)
        items.append(as_simulation_score(annotation))
        for key in ("input_tokens", "output_tokens"):
            usage[key] += tokens[key]
        usage["estimated"] |= tokens["estimated"]
    # Opportunity disagreement is a substantive prediction, not an invalid call.
    return {"items": items, "annotations": annotations,
            "rubric_version": record["rubric_version"], "contract_version": ASSESSMENT_CONTRACT}, usage
