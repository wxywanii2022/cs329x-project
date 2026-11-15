"""Strict JSON contracts shared by the runner and external role adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

BEHAVIORS = ("B1", "B2", "B3", "B4")
CONDITIONS = ("full", "without_assessment", "without_background", "no_coaching")
ROLES = ("learner", "assessment", "coach", "evaluator")
# RQ2 reuses the frozen RQ1 behavioral codebook and the evaluated output contract.
# They are separate versions: one defines labels, the other output and quote checks.
RUBRIC_VERSION = "v0.2"
ASSESSMENT_CONTRACT = "decision-point-v2"


class ValidationError(ValueError):
    """A configuration or role boundary violated its declared contract."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValidationError(message)


def keys(value: Any, required: set[str], optional: set[str] | None = None) -> None:
    require(isinstance(value, dict), "Expected a JSON object")
    require(required <= value.keys(), f"Missing keys: {required - value.keys()}")
    require(value.keys() <= required | (optional or set()),
            f"Unexpected keys: {value.keys() - required - (optional or set())}")


def string(value: Any, name: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{name} must be nonempty text")
    return value


def integer(value: Any, name: str, minimum: int = 0) -> int:
    require(type(value) is int and value >= minimum, f"{name} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class ModelSpec:
    adapter: str
    model_id: str
    family: str
    command: tuple[str, ...] = ()
    temperature: float = 0.7
    supports_seed: bool = False
    timeout_seconds: int = 120

    @classmethod
    def parse(cls, value: dict) -> ModelSpec:
        keys(value, {"adapter", "model_id", "family"},
             {"command", "temperature", "supports_seed", "timeout_seconds"})
        require(value["adapter"] in {"mock", "command"}, "Unknown adapter")
        for name in ("model_id", "family"):
            string(value[name], name)
        command = value.get("command", [])
        require(isinstance(command, list) and all(isinstance(x, str) and x for x in command),
                "command must be an argument list, never a shell string")
        require(value["adapter"] != "command" or bool(command), "command adapter needs command")
        temp = value.get("temperature", 0.7)
        require(type(temp) in (int, float) and 0 <= temp <= 2, "Invalid temperature")
        require(type(value.get("supports_seed", False)) is bool, "supports_seed must be boolean")
        integer(value.get("timeout_seconds", 120), "timeout_seconds", 1)
        return cls(**{**value, "command": tuple(command)})


@dataclass(frozen=True)
class Budget:
    max_coaching_turns: int = 2
    max_coaching_tokens: int = 4000
    max_output_tokens: int = 700
    max_context_bytes: int = 200000
    transport_attempts: int = 3

    @classmethod
    def parse(cls, value: dict) -> Budget:
        names = set(cls.__dataclass_fields__)
        keys(value, set(), names)
        for name, item in value.items():
            integer(item, name, 1)
        return cls(**value)


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int
    profiles: tuple[str, ...]
    pairs: tuple[str, ...]
    replicates: int
    orientations: tuple[str, ...]
    models: dict[str, ModelSpec]
    budget: Budget
    mode: str = "demo"
    split: str = "development"
    require_distinct_families: bool = False
    rubric_version: str = RUBRIC_VERSION

    @classmethod
    def parse(cls, value: dict) -> ExperimentConfig:
        keys(value, {"seed", "profiles", "pairs", "replicates", "orientations", "models"},
             {"budget", "mode", "split", "require_distinct_families", "rubric_version"})
        integer(value["seed"], "seed")
        integer(value["replicates"], "replicates", 1)
        for name in ("profiles", "pairs", "orientations"):
            items = value[name]
            require(isinstance(items, list) and bool(items), f"{name} must be a nonempty list")
            for item in items:
                string(item, name)
            require(len(items) == len(set(items)), f"Duplicate {name}")
        require(set(value["orientations"]) <= {"AB", "BA"}, "Orientations must be AB or BA")
        keys(value["models"], set(ROLES))
        models = {role: ModelSpec.parse(spec) for role, spec in value["models"].items()}
        mode = value.get("mode", "demo")
        require(mode in {"demo", "research"}, "mode must be demo or research")
        require(value.get("split", "development") in {"development", "test"}, "Unknown split")
        require(value.get("rubric_version", RUBRIC_VERSION) == RUBRIC_VERSION,
                "Unsupported rubric version; changing a name does not implement a rubric")
        distinct = value.get("require_distinct_families", False)
        require(type(distinct) is bool, "require_distinct_families must be boolean")
        if distinct:
            require(len({models[r].family for r in ("learner", "coach", "evaluator")}) == 3,
                    "Learner, coach and evaluator families must be distinct")
        if mode == "research":
            require(all(m.adapter != "mock" for m in models.values()),
                    "Research mode forbids mock roles")
            require(all("REPLACE" not in m.model_id and "REPLACE" not in m.family for m in models.values()),
                    "Replace example model IDs and family names before a research run")
        return cls(**{**value, "profiles": tuple(value["profiles"]), "pairs": tuple(value["pairs"]),
                      "orientations": tuple(value["orientations"]), "models": models,
                      "budget": Budget.parse(value.get("budget", {}))})


@dataclass(frozen=True)
class LearnerProfile:
    profile_id: str
    variant_id: str
    reporting_group: str
    initial_knowledge: tuple[str, ...]
    misconceptions: tuple[str, ...]
    habits: tuple[str, ...]
    domain_knowledge: str
    constraints: tuple[str, ...]
    initial_as_of: str

    @classmethod
    def parse(cls, value: dict) -> LearnerProfile:
        keys(value, set(cls.__dataclass_fields__))
        require(value["reporting_group"] in {"novice", "intermediate", "expert"}, "Unknown group")
        for name in ("initial_knowledge", "misconceptions", "habits", "constraints"):
            require(isinstance(value[name], list), f"{name} must be a list")
            for item in value[name]:
                string(item, name)
        for name in set(cls.__dataclass_fields__) - {"initial_knowledge", "misconceptions", "habits", "constraints"}:
            string(value[name], name)
        return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in value.items()})

    def background(self) -> dict:
        """Reporting groups and internal identifiers are never persona instructions."""
        return {k: v for k, v in asdict(self).items()
                if k not in {"profile_id", "variant_id", "reporting_group"}}


@dataclass(frozen=True)
class ScoreItem:
    behavior_id: str
    opportunity_status: str
    label: int | None
    na_reason: str | None
    evidence_message_ids: tuple[str, ...]
    supporting_spans: tuple[str, ...]
    brief_rationale: str

    @classmethod
    def parse(cls, value: dict, messages: list[dict]) -> ScoreItem:
        keys(value, set(cls.__dataclass_fields__))
        require(value["behavior_id"] in BEHAVIORS, "Unknown behavior")
        label = value["label"]
        require(label is None or (type(label) is int and label in (0, 1, 2)), "Invalid label")
        status = value["opportunity_status"]
        require(status in {"available", "no_opportunity", "insufficient_evidence"}, "Invalid opportunity")
        if label is None:
            require(status != "available" and value["na_reason"] == status,
                    "N/A must distinguish no_opportunity from insufficient_evidence")
        else:
            require(status == "available" and value["na_reason"] is None, "Scored item cannot be N/A")
        ids, spans = value["evidence_message_ids"], value["supporting_spans"]
        require(isinstance(ids, list) and isinstance(spans, list) and len(ids) == len(spans),
                "Each evidence message needs one supporting span")
        require(label is None or bool(ids), "Scorable labels require observable evidence")
        by_id = {m["message_id"]: m["content"] for m in messages}
        for mid, span in zip(ids, spans):
            require(isinstance(mid, str) and mid in by_id, "Unknown evidence message ID")
            require(isinstance(span, str) and 0 < len(span) <= 500 and span in by_id[mid],
                    "Supporting span must be an exact, short quote from its message")
        string(value["brief_rationale"], "brief_rationale")
        return cls(**{**value, "evidence_message_ids": tuple(ids), "supporting_spans": tuple(spans)})


def parse_scores(value: dict, messages: list[dict]) -> list[dict]:
    keys(value, {"items"})
    require(isinstance(value["items"], list), "items must be a list")
    items = [ScoreItem.parse(item, messages) for item in value["items"]]
    require(len(items) == 4 and {x.behavior_id for x in items} == set(BEHAVIORS),
            "Exactly one score for each of B1-B4 is required")
    return [asdict(item) for item in items]


def parse_decision(value: dict, bank: list[dict]) -> dict:
    keys(value, {"action", "exercise_id", "target_behavior", "brief_rationale"})
    string(value["brief_rationale"], "brief_rationale")
    require(value["action"] in {"exercise", "none"}, "Invalid coach action")
    if value["action"] == "none":
        require(value["exercise_id"] is None and value["target_behavior"] is None,
                "No intervention must have null exercise and target")
    else:
        exercise = next((x for x in bank if x["exercise_id"] == value["exercise_id"]), None)
        require(exercise is not None and exercise["behavior_id"] == value["target_behavior"],
                "Coach must choose one existing exercise with its matching target")
    return value


def parse_utterance(value: dict) -> dict:
    keys(value, {"content"})
    string(value["content"], "content")
    return value
