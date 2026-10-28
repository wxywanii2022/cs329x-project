"""Background-blind boundary for the team's frozen RQ1 module."""

import copy

from .evaluation import validate_record_scores


def assessment_payload(record: dict) -> dict:
    return copy.deepcopy({k: record[k] for k in ("task", "messages", "opportunities", "rubric_version")})


def assess(gateway, record: dict, **context):
    payload = assessment_payload(record)
    return gateway.call("assessment", payload,
                        lambda value: validate_record_scores(value, payload), **context)
