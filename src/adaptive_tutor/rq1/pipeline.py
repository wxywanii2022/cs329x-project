"""Standalone RQ1 runs: no reference labels are ever read during inference."""
from dataclasses import asdict
from pathlib import Path
from collections import Counter
import json
import csv
from ..schema import Budget, ModelSpec, ValidationError, keys, require, string
from ..storage import Journal, RunLock, digest, read_json, write_json, canonical
from ..adapters.base import Gateway, BudgetExceeded, RecordedFailure, check_response
from ..adapters.command import TransportError
from .core import prepare_payload, rubric_prompt, validate_annotation


def load_items(path, rubric="v0.2"):
    rows, identities, points = [], set(), set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        keys(item, {"item_id", "session_id", "behavior", "target_turn_id", "messages"},
             {"participant_id", "agent", "visible_instructions"})
        for field in ("item_id", "session_id"):
            string(item[field], field)
        for field in ("participant_id", "agent"):
            require(item.get(field) is None or isinstance(item[field], str) and bool(item[field].strip()), "Invalid metadata")
        point = (item["session_id"], item["target_turn_id"], item["behavior"])
        require(item["item_id"] not in identities and point not in points, "Duplicate item or decision point")
        identities.add(item["item_id"]); points.add(point)
        rows.append({"item_id": item["item_id"], "session_id": item["session_id"],
                     "participant_id": item.get("participant_id"), "agent": item.get("agent"),
                     "payload": prepare_payload(item, rubric)})
    require(bool(rows), "No assessment items")
    return rows


def split_check(items, split, development=None):
    require(split in {"development", "test"}, "Unknown split")
    if split == "development":
        require(development is None, "Development exclusion manifest is only for test runs")
        return {"split": split, "participant_disjoint_checked": False}
    require(development is not None, "Test runs require --development-items covering ALL prior development items")
    require(all(x.get("participant_id") for x in items + development), "Participant-disjoint test requires real linkage IDs; do not substitute session IDs")
    for field in ("participant_id", "session_id", "item_id"):
        require(not ({x[field] for x in items} & {x[field] for x in development}), f"Test/development {field} overlap")
    return {"split": split, "participant_disjoint_checked": True,
            "development_manifest_hash": digest(development),
            "limitation": "Checks supplied identifiers and declared development set only; cannot detect undeclared prior exposure."}


def load_config(path):
    raw = read_json(Path(path))
    keys(raw, {"model"}, {"seed", "budget", "rubric_version"})
    require(raw["model"] is not None, "Assessment model is not configured. Ask the model owner for the contract in docs/assessment.md; no default live model is selected.")
    model = ModelSpec.parse(raw["model"])
    seed = raw.get("seed", 329)
    require(type(seed) is int and seed >= 0, "Invalid seed")
    rubric = raw.get("rubric_version", "v0.2")
    rubric_prompt(rubric)
    return model, Budget.parse(raw.get("budget", {})), seed, rubric


def implementation_hashes():
    package = Path(__file__).parents[1]
    return {p.relative_to(package).as_posix(): digest(p.read_text(encoding="utf-8"))
            for p in sorted(package.rglob("*.py"))}


def run(items_path, config_path, output, split="development", development_path=None):
    model, budget, seed, rubric = load_config(config_path)
    items = load_items(items_path, rubric)
    development = load_items(development_path, rubric) if development_path else None
    split_info = split_check(items, split, development)
    require(not (split == "test" and model.adapter == "mock"), "Mock cannot produce a held-out model evaluation")
    frozen = {"schema_version": "rq1-run-v1", "items": items, "model": asdict(model),
              "budget": asdict(budget), "seed": seed, "rubric_version": rubric,
              "system_prompt": rubric_prompt(rubric), "split": split_info,
              "implementation_hashes": implementation_hashes()}
    # Normalize dataclass tuples to the exact JSON representation used on disk.
    frozen = json.loads(canonical(frozen))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    with RunLock(output):
        path = output / "frozen_inputs.json"
        if path.exists():
            require(read_json(path) == frozen, "Inputs/model/rubric/implementation changed; use a new output directory")
        else:
            require(not (output / "events.jsonl").exists(), "Journal exists without frozen inputs")
            write_json(path, frozen)
        journal = Journal(output / "events.jsonl", digest(frozen))
        require(all(e["config_hash"] == digest(frozen) for e in journal.events), "Journal belongs to another configuration")
        gateway = Gateway({"assessment": model}, budget, journal, seed)
        completed = {e["item_id"]: e["result"] for e in journal.events if e["kind"] == "assessment_item"}
        from .core import assess_point
        for item in items:
            if item["item_id"] in completed:
                continue
            payload = item["payload"]
            identity = {k: v for k, v in item.items() if k != "payload"}
            result = {**identity, "behavior": payload["behavior"], "target_turn_id": payload["target_turn_id"],
                      "rubric_version": rubric, "input_hash": digest(payload)}
            call_id = "rq1/" + digest(item["item_id"])
            try:
                annotation, usage = assess_point(gateway, payload, call_id=call_id, session_id=call_id,
                                                block_id=None, branch_id=None, phase="assessment")
                result.update(status="complete", annotation=annotation, usage=usage)
            except (ValidationError, BudgetExceeded, RecordedFailure, TransportError) as exc:
                result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            journal.append("assessment_item", item_id=item["item_id"], result=result)
        return export_run(output)


def audit_run(output, revalidate=False):
    """revalidate=True re-checks recorded responses of failed calls with the current validator
    (e.g. after a validator fix); no model is called and the journal is not modified."""
    output = Path(output)
    frozen = read_json(output / "frozen_inputs.json")
    events = Journal.read(output / "events.jsonl")
    require(all(e["config_hash"] == digest(frozen) for e in events), "Configuration hash mismatch")
    by_call = {"rq1/" + digest(x["item_id"]): x for x in frozen["items"]}
    results = {}
    call_results, failures, requests = {}, {}, {}
    for event in events:
        if event["kind"] == "call_attempt":
            request = event["request"]
            require(digest(request) == event["request_hash"], "Request hash mismatch")
            item = by_call[event["call_id"]]
            require(request["payload"] == item["payload"], "Inference evidence changed")
            require(request["system_prompt"] == frozen["system_prompt"], "Inference rubric changed")
            requests[event["call_id"]] = request
        elif event["kind"] == "call_result":
            call_results[event["call_id"]] = event
        elif event["kind"] == "call_failure":
            failures[event["call_id"]] = event
        elif event["kind"] == "assessment_item":
            require(event["item_id"] not in results, "Duplicate item outcome")
            results[event["item_id"]] = event["result"]
    for item in frozen["items"]:
        if item["item_id"] not in results:
            continue
        result = results[item["item_id"]]
        call_id = "rq1/" + digest(item["item_id"])
        require(result["input_hash"] == digest(item["payload"]), "Result input mismatch")
        if result["status"] == "complete":
            validate_annotation(result["annotation"], item["payload"])
            require(call_id in call_results and result["annotation"] == call_results[call_id]["response"]["output"], "Result differs from provider output")
        else:
            require(result["status"] == "failed" and "annotation" not in result and call_id in failures, "Failure must not become N/A")
            response = failures[call_id].get("response")
            if revalidate and response is not None:
                try:
                    annotation, usage = check_response(response, requests[call_id],
                                                       lambda x: validate_annotation(x, item["payload"]))
                except (ValidationError, TypeError, KeyError):
                    continue
                results[item["item_id"]] = {**{k: v for k, v in result.items() if k != "error"},
                                            "status": "complete", "annotation": annotation, "usage": usage,
                                            "revalidated_from_error": result["error"]}
    ordered = [results[x["item_id"]] for x in frozen["items"] if x["item_id"] in results]
    return frozen, ordered


def export_run(output):
    output = Path(output)
    frozen, results = audit_run(output)
    (output / "predictions.jsonl").write_text("".join(canonical(r) + "\n" for r in results), encoding="utf-8")
    fields = ["item_id", "session_id", "target_turn_id", "behavior", "status", "label", "reason", "confidence", "unclear_rule", "na_reason", "rubric_version", "input_hash"]
    with (output / "labels.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for r in results:
            annotation = r.get("annotation", {})
            row = {k: r.get(k, annotation.get(k, "")) for k in fields}
            row["label"] = ("N/A" if annotation["label"] is None else annotation["label"]) if annotation else ""
            # Model explanations and source identifiers are untrusted text when
            # opened in a spreadsheet. JSON/journal remain the exact source.
            row = {k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v)
                   for k, v in row.items()}
            writer.writerow(row)
    summary = {"items": len(frozen["items"]), "completed": sum(r["status"] == "complete" for r in results),
               "failed": sum(r["status"] == "failed" for r in results), "pending": len(frozen["items"]) - len(results),
               "labels": dict(Counter("N/A" if r["annotation"]["label"] is None else str(r["annotation"]["label"]) for r in results if r["status"] == "complete")),
               "rubric_version": frozen["rubric_version"], "model_id": frozen["model"]["model_id"],
               "split": frozen["split"], "mock_only": frozen["model"]["adapter"] == "mock",
               "validated_assessor": False}
    write_json(output / "summary.json", summary)
    return summary
