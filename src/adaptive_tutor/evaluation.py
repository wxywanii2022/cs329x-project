"""Blinded per-behavior evaluation and mechanical quality checks.

The evaluator applies the same frozen v0.2 codebook and v2 output contract as
the assessor, but as a separate role and model. Each behavior is scored from
the dialogue up to its own decision turn, so later turns, the answer key,
the final artifact and prescribed opportunity labels never reach it.
Artifact correctness is checked mechanically and reported separately, so it
cannot influence behavior labels.
"""

import re

from .assessment import decision_payload
from .rq1.core import as_simulation_score, rubric_prompt, validate_annotation
from .schema import ASSESSMENT_CONTRACT, BEHAVIORS, require


def blind_record(record: dict, blind_id: str) -> dict:
    # Allowlist: task messages and decision turn IDs only, no condition,
    # profile, answer key, artifact or prescribed opportunity status.
    return {"blind_record_id": blind_id, "rubric_version": record["rubric_version"],
            "messages": [{k: m[k] for k in ("message_id", "actor", "content")} for m in record["messages"]],
            "decision_message_ids": {b: record["opportunities"]["actual"][b]["decision_message_id"]
                                     for b in BEHAVIORS}}


def evaluator_payload(packet: dict, behavior: str) -> dict:
    return decision_payload(packet["messages"], behavior, packet["decision_message_ids"][behavior],
                            packet["rubric_version"])


def score_record(gateway, packet: dict, *, call_id: str, session_id: str, **context):
    items, annotations = [], []
    usage = {"input_tokens": 0, "output_tokens": 0, "estimated": False}
    prompt = rubric_prompt(packet["rubric_version"], ASSESSMENT_CONTRACT)
    for behavior in BEHAVIORS:
        payload = evaluator_payload(packet, behavior)
        annotation, tokens = gateway.call(
            "evaluator", payload, lambda value, p=payload: validate_annotation(value, p, ASSESSMENT_CONTRACT),
            call_id=f"{call_id}/{behavior}", session_id=f"{session_id}/{behavior}",
            prompt_text=prompt, prompt_version=ASSESSMENT_CONTRACT + "/" + packet["rubric_version"], **context)
        annotations.append(annotation)
        items.append(as_simulation_score(annotation))
        for key in ("input_tokens", "output_tokens"):
            usage[key] += tokens[key]
        usage["estimated"] |= tokens["estimated"]
    require({x["behavior_id"] for x in items} == set(BEHAVIORS), "Exactly one score for each of B1-B4 is required")
    return {"items": items, "annotations": annotations, "contract_version": ASSESSMENT_CONTRACT}, usage


def percentage(items: list[dict]) -> float | None:
    values = [item["label"] for item in items if item["label"] is not None]
    return 100 * sum(values) / (2 * len(values)) if values else None


def mechanical_checks(record: dict) -> dict:
    key = record["answer_key"]
    if not key:
        return {"arithmetic_correct": None, "source_reference_present": None, "source_references_valid": None}
    artifact = record["final_artifact"]
    percentages = [float(x) for x in re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%", artifact)]
    ids = {s["source_id"] for s in record["task"]["assistant_data"]}
    references = re.findall(r"\bSource\s+([\w-]+)", artifact)
    return {"arithmetic_correct": bool(percentages) and all(abs(x - key["growth_percent"]) < 1e-8 for x in percentages),
            "source_reference_present": key["source_id"] in artifact,
            "source_references_valid": all(ref in ids for ref in references) if references else None}
