"""Main 2 pre-launch checks; no model generation, no human labels read.

1. Session-held-out: no Main 2 session is a pilot (sampling plan list) or Main 1 session
   (data/rq1/main60/items.jsonl), and decision points are unique.
2. Byte admission: rebuild every Gateway request exactly as Gateway.call does for every
   configs/main2 config and seed; all must fit max_context_bytes.
3. Token window (--tokens; needs the pinned tokenizers in the local HF cache): count the
   chat-templated prompt local_vllm sends (system + canonical payload, generation prompt,
   enable_thinking) and require input + max_output_tokens <= --max-model-len.

Writes one JSON record; refuses to overwrite. Exit code 1 if any check fails.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from adaptive_tutor.rq1.core import prepare_payload, rubric_prompt
from adaptive_tutor.rq1.pipeline import load_config, load_items
from adaptive_tutor.storage import canonical, digest

SEEDS = (329, 330, 331)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def records(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").split("\n") if line.strip()]


def request_for(item, model, budget, rubric, contract, seed):
    call_id = "rq1/" + digest(item["item_id"])
    return dict(protocol_version="1", role="assessment", session_id=call_id,
                system_prompt=rubric_prompt(rubric, contract), prompt_version=contract + "/" + rubric,
                payload=prepare_payload(item, rubric), sample_seed=int(digest([seed, call_id])[:8], 16),
                model=dict(model_id=model.model_id, temperature=model.temperature, supports_seed=model.supports_seed),
                limits=dict(max_output_tokens=budget.max_output_tokens, max_total_tokens=None))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--items", type=Path, default=PROJECT / "data/rq1/main2/items.jsonl")
    ap.add_argument("--sampling-plan", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--tokens", action="store_true")
    ap.add_argument("--max-model-len", type=int, default=131072)
    args = ap.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite an existing preflight record")
    items = records(args.items)
    assert len(load_items(args.items)) == len(items) == 60
    plan = json.loads(args.sampling_plan.read_text())
    pilot = set(plan["excluded_pilot_sessions"])
    main1 = {x["session_id"] for x in records(PROJECT / "data/rq1/main60/items.jsonl")}
    plan_main1 = set(plan["excluded_main1_sessions"])
    sessions = [x["session_id"] for x in items]
    heldout = dict(
        main2_sessions=len(set(sessions)), main2_items=len(items),
        pilot_sessions=len(pilot), main1_sessions=len(main1),
        plan_main1_list_matches_repo_main1=plan_main1 == main1,
        overlap_with_pilot=sorted(set(sessions) & pilot), overlap_with_main1=sorted(set(sessions) & main1),
        participant_disjoint=False,
        note="Session-held-out only; 16 of 60 items come from participants seen in earlier rounds (see sampling-audit.json).")
    ok = (len(set(sessions)) == 60 and not heldout["overlap_with_pilot"] and not heldout["overlap_with_main1"]
          and heldout["plan_main1_list_matches_repo_main1"] and len(pilot) == 20 and len(main1) == 60)
    heldout["pass"] = ok

    configs = sorted((PROJECT / "configs/main2").glob("assessment.*.json"))
    bytes_rows, token_rows, tokenizers = [], [], {}
    for path in configs:
        model, budget, _, rubric, contract = load_config(path)
        for seed in SEEDS:
            sizes = {x["item_id"]: len(canonical(request_for(x, model, budget, rubric, contract, seed)).encode("utf-8"))
                     for x in items}
            over = {k: v for k, v in sizes.items() if v > budget.max_context_bytes}
            ok &= not over
            bytes_rows.append(dict(config=path.name, config_sha256=sha(path), seed=seed,
                                   max_context_bytes=budget.max_context_bytes,
                                   max_request_bytes=max(sizes.values()),
                                   argmax=max(sizes, key=sizes.get), over_budget=over))
        if args.tokens:
            from transformers import AutoTokenizer
            repo, revision = model.model_id.split("@")
            if model.model_id not in tokenizers:
                tokenizers[model.model_id] = AutoTokenizer.from_pretrained(repo, revision=revision, local_files_only=True)
            tok = tokenizers[model.model_id]
            counts = {}
            for x in items:  # seed does not enter the prompt text
                req = request_for(x, model, budget, rubric, contract, SEEDS[0])
                messages = [{"role": "system", "content": req["system_prompt"]},
                            {"role": "user", "content": canonical(req["payload"])}]
                ids = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                              enable_thinking=True)
                if isinstance(ids, dict) or hasattr(ids, "keys"):
                    ids = ids["input_ids"]
                counts[x["item_id"]] = len(ids)
            limit = args.max_model_len - budget.max_output_tokens
            over = {k: v for k, v in counts.items() if v > limit}
            ok &= not over
            token_rows.append(dict(config=path.name, model_id=model.model_id, max_input_tokens=max(counts.values()),
                                   argmax=max(counts, key=counts.get), input_limit=limit, over_limit=over,
                                   top5={k: counts[k] for k in sorted(counts, key=counts.get, reverse=True)[:5]}))
    record = dict(
        recorded_at_utc=datetime.now(timezone.utc).isoformat(), script_sha256=sha(__file__),
        items_sha256=sha(args.items), sampling_plan_sha256=sha(args.sampling_plan),
        model_generation_calls=0, human_labels_read=False,
        heldout=heldout, byte_admission=bytes_rows,
        token_window=token_rows if args.tokens else "not run in this invocation",
        max_model_len=args.max_model_len, passed=bool(ok))
    if args.tokens:
        import transformers
        record["transformers_version"] = transformers.__version__
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as f:
        json.dump(record, f, indent=1)
    print(json.dumps(dict(passed=record["passed"], heldout=heldout["pass"],
                          max_bytes=max(r["max_request_bytes"] for r in bytes_rows),
                          tokens=[(r["config"], r["max_input_tokens"], r["argmax"]) for r in token_rows])))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
