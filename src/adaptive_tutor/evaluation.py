"""Blinded one-record evaluation, evidence validation and mechanical quality checks."""

import copy
import re

from .schema import BEHAVIORS, parse_scores, require


def validate_record_scores(value: dict, record: dict) -> dict:
    items = parse_scores(value, record["messages"])
    positions = {m["message_id"]: i for i, m in enumerate(record["messages"])}
    for item in items:
        opportunity = record["opportunities"]["actual"][item["behavior_id"]]
        require(item["opportunity_status"] == opportunity["status"],
                "Scoring must preserve the recorded opportunity status")
        cutoff = opportunity["decision_message_id"]
        if cutoff is not None:
            require(all(positions[mid] <= positions[cutoff] for mid in item["evidence_message_ids"]),
                    "Score evidence cannot use messages after the decision point")
    return {"items": items}


def blind_record(record: dict, blind_id: str) -> dict:
    # Allowlist rather than deleting a growing list of private metadata fields.
    packet = copy.deepcopy({k: record[k] for k in
                            ("task", "messages", "opportunities", "answer_key", "final_artifact", "rubric_version")})
    packet["blind_record_id"] = blind_id
    for message in packet["messages"]:
        message["actor"] = {"task_agent": "assistant", "environment": "evidence", "learner": "user"}[message["actor"]]
    return packet


def score_record(gateway, packet: dict, **context):
    return gateway.call("evaluator", packet, lambda value: validate_record_scores(value, packet), **context)


def percentage(items: list[dict]) -> float | None:
    values = [item["label"] for item in items if item["label"] is not None]
    return 100 * sum(values) / (2 * len(values)) if values else None


def mechanical_checks(record: dict) -> dict:
    key = record["answer_key"]
    if not key:
        return {"arithmetic_correct": None, "source_reference_present": None, "source_references_valid": None}
    artifact = record["final_artifact"]
    percentages = [float(x) for x in re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%", artifact)]
    ids = {s["source_id"] for s in record["task"]["sources"]}
    references = re.findall(r"\bSource\s+([\w-]+)", artifact)
    return {"arithmetic_correct": bool(percentages) and all(abs(x - key["growth_percent"]) < 1e-8 for x in percentages),
            "source_reference_present": key["source_id"] in artifact,
            "source_references_valid": all(ref in ids for ref in references) if references else None}
