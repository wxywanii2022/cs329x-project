"""Offline audit and transcript replay. Never invokes a model."""

from pathlib import Path

from .evaluation import validate_record_scores
from .schema import CONDITIONS, require
from .storage import Journal, digest, fork_snapshot, read_json


def audit_run(output: Path) -> dict:
    manifest = read_json(output / "manifest.json")
    bundle = read_json(output / "frozen_inputs.json")
    require(digest(bundle) == manifest["config_hash"], "Frozen input hash mismatch")
    events = Journal.read(output / "events.jsonl")
    require(all(e["config_hash"] == manifest["config_hash"] for e in events), "Event configuration mismatch")
    for event in events:
        if event["kind"] == "artifact":
            artifact_path = (output / event["path"]).resolve()
            require(artifact_path.is_relative_to(output.resolve()), "Artifact path escapes run directory")
            require(digest(read_json(artifact_path)) == event["content_hash"], "Export/checkpoint hash mismatch")
    successes = {e["call_id"]: e for e in events if e["kind"] == "call_result"}
    for event in events:
        if event["kind"] != "call_attempt":
            continue
        request = event["request"]
        require(digest(request) == event["request_hash"], "Recorded request hash mismatch")
        if event["call_id"] in successes:
            require(successes[event["call_id"]]["request_hash"] == event["request_hash"], "Request/result mismatch")
        role, payload = request["role"], request["payload"]
        if role == "learner":
            require(set(payload) == {"initial_background", "observed_history", "task", "stage"}, "Learner payload leak")
        elif role == "assessment":
            from .rq1.core import validate_payload
            from .assessment import assessment_payload
            validate_payload(payload)
            # Compare with a fresh prefix of the original task, not merely the
            # model's quoted IDs. Oracle status and future text must be absent.
            pre = read_json(output / "blocks" / event["block_id"] / "pre.json")["record"]
            require(payload == assessment_payload(pre, payload["behavior"]), "Assessment prefix mismatch")
        elif role == "coach":
            condition = event["branch_id"]
            allowed = {"task", "messages", "exercise_bank"}
            if condition != "without_assessment":
                allowed.add("assessment")
            if condition != "without_background":
                allowed.add("background")
            require(condition != "no_coaching" and set(payload) == allowed, "Coach masking violation")
        else:
            require(set(payload) == {"blind_record_id", "task", "messages", "opportunities", "answer_key", "final_artifact", "rubric_version"},
                    "Evaluator payload leak")
        if role != "assessment":
            require(set(payload["task"]) == {"instructions", "sources", "requirements"}, "Private task metadata leaked")
    count = 0
    for block in manifest["blocks"]:
        if not block.get("snapshot_hash"):
            continue
        folder = output / "blocks" / block["block_id"]
        root = read_json(folder / "pre.json")["snapshot"]
        require(fork_snapshot(root)["snapshot_hash"] == block["snapshot_hash"], "Manifest root mismatch")
        sessions = set()
        for condition in CONDITIONS:
            branch = block["branches"][condition]
            require(branch["snapshot_hash"] == root["snapshot_hash"], "Branches started at different roots")
            checkpoint = read_json(folder / "branches" / condition / "result.json")
            for key, value in branch.items():
                require(checkpoint[key] == value, "Manifest and branch checkpoint differ")
            initial = read_json(folder / "branches" / condition / "initial_state.json")
            require(initial["snapshot_hash"] == root["snapshot_hash"], "Initial state hash mismatch")
            require(initial["learner_session_id"] not in sessions, "Learner sessions shared across branches")
            sessions.add(initial["learner_session_id"])
            if checkpoint["status"] == "complete":
                require(checkpoint["final_state"]["messages"][:len(root["messages"])] == root["messages"], "Lost pre-task history")
                require(branch["coaching_turns"] <= bundle["config"]["budget"]["max_coaching_turns"], "Turn budget violated")
                require(branch["coaching_tokens"] <= bundle["config"]["budget"]["max_coaching_tokens"], "Token budget violated")
        record_ids = [block["pre_packet"], *(b["packet"] for b in block["branches"].values() if b.get("packet"))]
        for blind_id in record_ids:
            packet = read_json(output / "blinded" / f"{blind_id}.json")
            require(packet["blind_record_id"] == blind_id, "Packet identity mismatch")
            scores = read_json(output / "scores" / f"{blind_id}.json")
            if scores["status"] == "complete":
                validate_record_scores({"items": scores["items"]}, packet)
            count += 1
    return {"status": "passed", "blocks": len(manifest["blocks"]), "task_records": count,
            "events": len(events), "failed_branches": manifest["failed_branches"], "failed_scores": manifest["failed_scores"]}


def replay(output: Path) -> list[dict]:
    audit_run(output)
    return [{k: e[k] for k in ("block_id", "branch_id", "phase", "message_id", "actor", "visible_content")}
            for e in Journal.read(output / "events.jsonl") if e["kind"] == "message"]
