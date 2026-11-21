"""Read-only Main 2 sampling replay and exact Gateway byte audit; no inference.

Requires networkx==3.5 for replay of the frozen local sampler. Reads private
artifacts locally; writes only hashes, counts and item IDs, never source text.
Does not run the sampler's freeze/build commands or instantiate a Gateway.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from adaptive_tutor.rq1.core import prepare_payload, rubric_prompt
from adaptive_tutor.rq1.pipeline import load_config, load_items
from adaptive_tutor.storage import canonical, digest


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def records(path):
    return [json.loads(line) for line in path.read_text().split("\n") if line.strip()]


def screen(rows, patterns):
    """Independent implementation of the plan's fixed lexical/structural rules."""
    eligible = {b: [] for b in ("B1", "B2", "B3", "B4")}
    assistant = None
    for i, row in enumerate(rows):
        text = row.get("content", "")
        if row.get("role") == "assistant" and text.strip():
            assistant = text
        if not (row.get("role") == "user" and row.get("is_conversational") is True
                and text.strip() and not text.strip().startswith("/")):
            continue
        if (eligible["B1"] and assistant
                and re.search(patterns["preceding_assistant_claim_proxy"], assistant, re.I)):
            eligible["B3"].append(i)
            eligible["B4"].append(i)
        if all(re.search(patterns[k], text, re.I) for k in ("request", "output")):
            eligible["B2"].append(i)
        eligible["B1"].append(i)
    return eligible


def audit(root):
    import networkx
    folder = root / "annotation_main2"
    artifacts = {name: {"path": "annotation_main2/" + name,
                        "sha256": sha(folder / name), "bytes": (folder / name).stat().st_size}
                 for name in ("sampling_plan.json", "selection_manifest.json")}
    plan = json.loads((folder / "sampling_plan.json").read_text())
    manifest = json.loads((folder / "selection_manifest.json").read_text())
    assert networkx.__version__ == plan["dependencies"]["networkx"]
    assert artifacts["sampling_plan.json"]["sha256"] == manifest["plan_sha256"]
    assert plan["frozen_at_utc"] < manifest["selected_at_utc"]
    # Verify the recorded dependencies at their archived paths before importing
    # the frozen allocator. No raw artifact is copied to this repository.
    assert all(sha(path) == expected for path, expected in plan["dependencies_sha256"].items())
    builder_path = root / "scripts/prepare_main2.py"
    assert sha(builder_path) == next(v for k, v in plan["dependencies_sha256"].items()
                                    if Path(k).name == "prepare_main2.py")
    spec = importlib.util.spec_from_file_location("frozen_main2_sampler", builder_path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    data = root / "data/collabskill_public"
    meta = {s["session_id"]: s for s in json.loads((data / "leaderboard_data/sessions.json").read_text())}
    main1 = json.loads((root / "annotation_main60/selection_manifest.json").read_text())
    assert set(plan["excluded_pilot_sessions"]) == set(main1["excluded_pilot_sessions"])
    assert set(plan["excluded_main1_sessions"]) == {x["session_id"] for x in main1["items"]}
    excluded = set(plan["excluded_pilot_sessions"] + plan["excluded_main1_sessions"])
    assert len(excluded) == 80
    prior = {str(meta[s]["user_id"]) for s in excluded}
    assert prior == set(plan["prior_participants"])
    candidates, logs, hashes = {}, {}, {}
    eligible_total = 0
    for path in sorted((data / "interaction_logs").glob("*/extracted_log.jsonl")):
        sid = path.parent.name
        rows = records(path)
        turns = screen(rows, plan["patterns"])
        if len(turns["B1"]) < 2:
            continue
        eligible_total += 1
        if sid in excluded:
            continue
        assert turns == builder.eligible_turns(rows, plan["patterns"])
        pid = str(meta[sid]["user_id"])
        candidates[sid] = dict(agent=meta[sid]["agent_id"], participant_id=pid,
                               unseen_participant=pid not in prior, turns=turns)
        logs[sid], hashes[sid] = rows, sha(path)
    assert eligible_total == manifest["eligible_sessions"] == 226
    assert len(candidates) == manifest["remaining_sessions"] == 146
    assert hashes == manifest["source_log_sha256"]
    counts = {a: {b: sum(c["agent"] == a and bool(c["turns"][b]) for c in candidates.values())
                  for b in plan["behaviors"]} for a in plan["agents"]}
    assert counts == manifest["candidate_counts_by_cell"]
    # Deterministic replay ONLY: compare in memory, never write a new selection.
    assignment = builder.allocate(candidates, plan["items_per_agent_behavior"],
                                  plan["seeds"]["assignment_priorities"], plan["agents"])
    rng = random.Random(plan["seeds"]["target_turn"])
    replay = []
    for sid, behavior in sorted(assignment):
        c = candidates[sid]
        index = rng.choice(c["turns"][behavior])
        replay.append(dict(session_id=sid, behavior=behavior, agent=c["agent"],
                           participant_id=c["participant_id"], unseen_participant=c["unseen_participant"],
                           target_record_index=index, target_turn_id=str(logs[sid][index]["turn_id"]),
                           source_sha256=hashes[sid]))
    random.Random(plan["seeds"]["display_order"]).shuffle(replay)
    for i, row in enumerate(replay, 1):
        row["item_id"] = f"M2-{i:03d}"
    assert replay == manifest["items"], "Frozen draw/targets/order do not reproduce"
    assert len(replay) == len({r["session_id"] for r in replay}) == 60
    quotas = Counter((r["agent"], r["behavior"]) for r in replay)
    assert all(quotas[a, b] == 3 for a in plan["agents"] for b in plan["behaviors"])
    selected_passes = Counter()
    for row in replay:
        assert row["target_record_index"] in candidates[row["session_id"]]["turns"][row["behavior"]]
        selected_passes[row["behavior"]] += 1
    main2_path = folder / "ready/coordinator_only/items.jsonl"
    items = records(main2_path)
    assert len(load_items(main2_path)) == len(items) == 60
    main1_path = PROJECT / "data/rq1/main60/items.jsonl"
    main1_items = records(main1_path)
    assert len(load_items(main1_path)) == len(main1_items) == 60
    for item, selected in zip(items, replay):
        assert all(item[k] == selected[k] for k in
                   ("item_id", "session_id", "participant_id", "agent", "behavior", "target_turn_id"))
        messages, _ = builder.redact_prefix(logs[selected["session_id"]][:selected["target_record_index"]+1])
        assert messages == item["messages"]
    groups = []
    configs = {}
    for version in ("v2", "v3"):
        for model_key in ("qwen38-27b-fp8", "qwen35-9b"):
            config = PROJECT / f"configs/{version}/assessment.{model_key}.json"
            model, budget, _, rubric, contract = load_config(config)
            configs[str(config.relative_to(PROJECT))] = sha(config)
            assert budget.max_context_bytes == 200000 and budget.max_output_tokens == 32768
            for dataset, batch in (("main1", main1_items),
                                   ("main2", items)):
                for seed in (329, 330, 331):
                    sizes = {}
                    for item in batch:
                        call_id = "rq1/" + digest(item["item_id"])
                        request = dict(protocol_version="1", role="assessment", session_id=call_id,
                                       system_prompt=rubric_prompt(rubric, contract),
                                       prompt_version=contract + "/" + rubric,
                                       payload=prepare_payload(item, rubric),
                                       sample_seed=int(digest([seed, call_id])[:8], 16),
                                       model=dict(model_id=model.model_id, temperature=model.temperature,
                                                  supports_seed=model.supports_seed),
                                       limits=dict(max_output_tokens=budget.max_output_tokens, max_total_tokens=None))
                        sizes[item["item_id"]] = len(canonical(request).encode("utf-8"))
                    groups.append(dict(dataset=dataset, contract=version, model=model_key, seed=seed,
                                       items=len(batch), max_request_bytes=max(sizes.values()),
                                       exceeds_200000={i: n for i, n in sizes.items() if n > 200000},
                                       exceeds_300000={i: n for i, n in sizes.items() if n > 300000},
                                       focus_items={i: n for i, n in sizes.items() if i in {"M1-009", "M2-046", "M2-047"}}))
    participants = Counter(r["participant_id"] for r in replay)
    return dict(audited_at_utc=datetime.now(timezone.utc).isoformat(),
                audit_script_sha256=sha(__file__), artifacts=artifacts,
                original_local_freeze_utc=plan["frozen_at_utc"], original_selection_utc=manifest["selected_at_utc"],
                provenance="Post-selection audit of a recorded local pre-selection freeze; not proof of an earlier public registration.",
                model_calls=0, labels_generated=0, human_annotations_read=False,
                dependencies_and_all_146_candidate_source_hashes_verified=True,
                assignment_targets_and_display_order_reproduce_exactly=True,
                source_prefix_and_redacted_model_materials_match=True,
                source_scope=dict(eligible_sessions=eligible_total, remaining_sessions=len(candidates),
                                  excluded_pilot_and_main1_sessions=len(excluded), selected_session_overlap=0),
                candidate_sessions_by_agent_behavior=counts,
                eligible_turn_counts={b: sum(len(c["turns"][b]) for c in candidates.values()) for b in plan["behaviors"]},
                selected_screen_pass_counts=dict(sorted(selected_passes.items())),
                selected_each_agent_behavior=3, selected_unique_sessions=60,
                selected_participants=len(participants), selected_max_items_per_participant=max(participants.values()),
                selected_unseen_participant_items=sum(r["unseen_participant"] for r in replay),
                selected_seen_participant_items=sum(not r["unseen_participant"] for r in replay),
                interpretation="B2/B3/B4 are proxy-enriched by hard eligibility screens, not human-verified opportunities; B1 is unscreened. B4 has no visible-problem detector. This is not uniform population sampling.",
                main2_items_sha256=sha(main2_path), frozen_config_sha256=configs,
                byte_measurement="len(canonical(Gateway request).encode('utf-8')); includes prompt and envelope, not just dialogue; no Gateway or adapter instantiated",
                current_max_context_bytes=200000, proposed_max_context_bytes=300000,
                token_window_preflight="NOT PERFORMED; byte admission does not certify token-window or GPU feasibility",
                byte_audit=groups)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Do not overwrite an audit")
    result = audit(args.research_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("PASS: exact frozen draw reproduced; 60 screen checks; 1,440 request sizes; zero model calls.")
    print("Proxy-eligible turns:", result["eligible_turn_counts"])
    print("Largest request:", max(g["max_request_bytes"] for g in result["byte_audit"]), "bytes")


if __name__ == "__main__":
    main()
