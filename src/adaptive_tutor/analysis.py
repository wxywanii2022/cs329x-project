"""Traceable paired exports; N/A stays missing and blocks stay paired."""

from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from .evaluation import percentage
from .schema import BEHAVIORS, CONDITIONS, require
from .storage import Journal, read_json, write_json


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _score(output, blind_id):
    if blind_id is None:
        return None
    result = read_json(output / "scores" / f"{blind_id}.json")
    return result if result["status"] == "complete" else None


def _percent(score):
    return percentage(score["items"]) if score else None


def _difference(left, right):
    return left - right if left is not None and right is not None else None


def _available(score):
    return [x["behavior_id"] for x in score["items"] if x["label"] is not None] if score else []


def export_analysis(output: Path) -> dict:
    manifest = read_json(output / "manifest.json")
    results, behaviors, human = [], [], []
    for block in manifest["blocks"]:
        pre = _score(output, block["pre_packet"])
        control = _score(output, block["branches"]["no_coaching"].get("packet"))
        pre_pct, control_pct = _percent(pre), _percent(control)
        record_ids = [("pre", None, block["pre_packet"])]
        for condition in CONDITIONS:
            branch = block["branches"][condition]
            post = _score(output, branch.get("packet"))
            post_pct = _percent(post)
            gain = _difference(post_pct, pre_pct)
            contrast = _difference(gain, _difference(control_pct, pre_pct))
            comparable = bool(pre and post and control and set(_available(pre)) == set(_available(post)) == set(_available(control)))
            na = {x["behavior_id"]: x["na_reason"] for x in post["items"] if x["label"] is None} if post else {}
            branch_file = output / "blocks" / block["block_id"] / "branches" / condition / "result.json"
            record = read_json(branch_file).get("record", {}) if branch_file.exists() else {}
            opportunity = record.get("opportunities", {}).get("actual", {}).get("B4", {}).get("status")
            row = {"block_id": block["block_id"], "profile_id": block["profile_id"],
                   "reporting_group": block["reporting_group"], "pair_id": block["pair_id"],
                   "orientation": block["orientation"], "replicate": block["replicate"], "condition": condition,
                   "status": branch["status"], "score_status": "complete" if post else "unavailable",
                   "pre_percent": pre_pct, "post_percent": post_pct, "gain_pp": gain,
                   "paired_effect_pp": contrast, "comparable_opportunities": comparable,
                   "comparable_effect_pp": contrast if comparable else None,
                   "pre_scorable": ";".join(_available(pre)), "post_scorable": ";".join(_available(post)),
                   "na_reasons": ";".join(f"{b}:{reason}" for b, reason in na.items()),
                   "snapshot_hash": block.get("snapshot_hash"), "pre_record_id": block["pre_packet"],
                   "post_record_id": branch.get("packet"), "coaching_turns": branch.get("coaching_turns", 0),
                   "coaching_tokens": branch.get("coaching_tokens", 0), "coaching_status": branch.get("coaching_status"),
                   "exercise_id": (branch.get("decision") or {}).get("exercise_id"),
                   "targeted_error_opportunity": 1 if opportunity == "available" else 0,
                   "targeted_error": (int(not record["mechanical_checks"]["arithmetic_correct"])
                                      if opportunity == "available" and record.get("mechanical_checks") else None),
                   "discovery": record.get("discovery"),
                   "spontaneous_check_then_correction": record.get("natural_chain_completed"),
                   "task_agent_help_count": record.get("task_agent_help_count"),
                   "error": branch.get("error", "")}
            results.append(row)
            record_ids.append(("post", condition, branch.get("packet")))
        for phase, condition, blind_id in record_ids:
            if blind_id is None:
                continue
            scores = _score(output, blind_id)
            for behavior in BEHAVIORS:
                human.append({"blind_record_id": blind_id, "behavior_id": behavior,
                              "annotator": "", "label": "", "reason": ""})
            if scores:
                for item in scores["items"]:
                    behaviors.append({"block_id": block["block_id"], "phase": phase, "condition": condition,
                                      "blind_record_id": blind_id, "snapshot_hash": block.get("snapshot_hash"),
                                      "rubric_version": scores["rubric_version"], **item,
                                      "evidence_message_ids": ";".join(item["evidence_message_ids"]),
                                      "supporting_spans": " | ".join(item["supporting_spans"])})
    analysis_dir = output / "analysis"
    result_fields = list(results[0]) if results else ["block_id", "condition", "status"]
    write_csv(analysis_dir / "results.csv", results, result_fields)
    write_csv(analysis_dir / "behavior_scores.csv", behaviors,
              ["block_id", "phase", "condition", "blind_record_id", "snapshot_hash", "rubric_version",
               "behavior_id", "opportunity_status", "label", "na_reason", "evidence_message_ids", "supporting_spans", "brief_rationale"])
    # The template is shuffled independently and contains no unblinding columns.
    random.Random(781).shuffle(human)
    template_path = output / "blinded" / "human_labels_template.csv"
    if not template_path.exists():
        write_csv(template_path, human, ["blind_record_id", "behavior_id", "annotator", "label", "reason"])
    groups = defaultdict(list)
    for row in results:
        groups[row["reporting_group"], row["condition"]].append(row)
    summaries = []
    for (group, condition), rows in sorted(groups.items()):
        usable = [r for r in rows if r["paired_effect_pp"] is not None]
        clusters = defaultdict(list)
        for row in usable:
            clusters[row["pair_id"]].append(row["paired_effect_pp"])
        interval = None
        if len(clusters) >= 2:
            rng, estimates, pairs = random.Random(7), [], sorted(clusters)
            for _ in range(1000):
                sampled = [value for pair in rng.choices(pairs, k=len(pairs)) for value in clusters[pair]]
                estimates.append(mean(sampled))
            estimates.sort()
            interval = [estimates[24], estimates[974]]
        denominators = sum(r["targeted_error_opportunity"] for r in rows)
        summaries.append({"reporting_group": group, "condition": condition, "blocks": len(rows),
                          "complete_pairs": len(usable), "failed_branches": sum(r["status"] != "complete" for r in rows),
                          "paired_effect_pp": mean(r["paired_effect_pp"] for r in usable) if usable else None,
                          "comparable_effect_pp": mean(vals) if (vals := [r["comparable_effect_pp"] for r in rows if r["comparable_effect_pp"] is not None]) else None,
                          "task_pair_clusters": len(clusters), "cluster_bootstrap_95_interval": interval,
                          "targeted_error_count": sum(r["targeted_error"] or 0 for r in rows),
                          "targeted_error_opportunities": denominators,
                          "no_intervention_count": sum(r["coaching_status"] == "none" for r in rows),
                          "coaching_turns": sum(r["coaching_turns"] for r in rows)})
    journal = Journal.read(output / "events.jsonl")
    usage = Counter()
    for event in journal:
        tokens = event.get("usage") or event.get("response", {}).get("usage")
        if tokens and all(type(tokens.get(k)) is int for k in ("input_tokens", "output_tokens")):
            usage["input_tokens"] += tokens["input_tokens"]
            usage["output_tokens"] += tokens["output_tokens"]
            usage["estimated_usage_calls"] += int(bool(tokens.get("estimated")))
    summary = {"mode": manifest["mode"], "groups": summaries, "usage": dict(usage),
               "transport_failures": sum(e["kind"] == "transport_failure" for e in journal),
               "transport_attempts_with_unknown_usage": sum(e["kind"] == "transport_failure" for e in journal),
               "failed_scores": manifest["failed_scores"],
               "interpretation": "Mock runs validate infrastructure only. Intervals require at least two task-pair clusters; no powered-design or human-learning claim is implied."}
    write_json(analysis_dir / "summary.json", summary)
    return summary


def agreement(left: list[str], right: list[str]) -> dict:
    require(len(left) == len(right) and bool(left), "Agreement needs matching nonempty label lists")
    labels = ["0", "1", "2", "N/A"]
    require(set(left + right) <= set(labels), "Unknown annotation label")
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    a, b = Counter(left), Counter(right)
    expected = sum(a[label] * b[label] for label in labels) / len(left) ** 2
    return {"n": len(left), "raw_agreement": observed,
            "cohen_kappa": (observed - expected) / (1 - expected) if expected < 1 else None,
            "labels": labels, "confusion": [[sum(x == i and y == j for x, y in zip(left, right)) for j in labels] for i in labels],
            "false_missed_count": sum(x != "0" and y == "0" for x, y in zip(left, right)),
            "non_missed_reference_count": sum(x != "0" for x in left)}


def compare_annotations(reference: Path, candidate: Path) -> dict:
    def load(path):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        result = {}
        for row in rows:
            key = (row["blind_record_id"], row["behavior_id"])
            require(key not in result, "Duplicate annotation key; compare one annotator per file")
            require(row["label"] in {"0", "1", "2", "N/A"}, "Fill every label; use N/A explicitly")
            result[key] = row["label"]
        return result
    left, right = load(reference), load(candidate)
    require(left.keys() == right.keys(), "Annotation files must contain the same decision points")
    order = sorted(left)
    return agreement([left[k] for k in order], [right[k] for k in order])
