"""Replay pilot coach decisions with another coach prompt, holding every input fixed.

    python3 scripts/rq2_coach_replay.py --pilot outputs/rq2-pilot --output outputs/rq2-coach-replay \
        --prompt src/adaptive_tutor/prompts/coach_v2.txt [--config configs/rq2-pilot/pilot.json]

For every accepted coach decision in the pilot's journals, this re-sends the recorded
request (same payload, model, limits and sample seed) with only the system prompt
replaced, through the same command adapter and decision validator the runner uses.
TUTOR_COACH_LOCAL_URL must point at the coach's loopback vLLM server. Results go to
<output>/decisions.jsonl (resumable: finished call IDs are skipped) and a summary to
<output>/summary.md. A replay isolates the prompt; the learners never see these
decisions, so it says nothing about practice uptake or post-task effects.

--no-gap is the adaptation-sanity check for the full coach. Pilot 2 had no block where the
assessor found no gap, so "none when no gap" could not be observed. This mode replays only
full-condition decisions with the same prompt and inputs, except that every assessor label 0
or 1 is rewritten to 2 (with a neutral reason); 2 and null stay. The messages are unchanged
and the prompt tells the coach to check the assessment against them, so the summary also
reports the blocks where the without_assessment coach, reading the same messages, chose none.
"""

import argparse
import collections
import concurrent.futures
import copy
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from adaptive_tutor.adapters.command import CommandAdapter, TransportError  # noqa: E402
from adaptive_tutor.schema import ExperimentConfig, ValidationError, parse_decision  # noqa: E402
from adaptive_tutor.storage import read_json  # noqa: E402


def recorded_decisions(pilot: Path):
    """Yield (shard, block, request, v1 decision) for each accepted coach decision."""
    for events_path in sorted(pilot.glob("shards/*/events.jsonl")):
        shard = events_path.parent
        attempts, results = {}, {}
        for line in events_path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("actor") != "coach" or not event.get("call_id", "").endswith("/decision"):
                continue
            if event["kind"] == "call_attempt":
                attempts.setdefault(event["call_id"], event["request"])
            elif event["kind"] == "call_result":
                results[event["call_id"]] = event["response"]["output"]
        for call_id, output in sorted(results.items()):
            block_id = call_id.split("/")[0]
            block_dir = shard / "blocks" / block_id
            yield shard, read_json(block_dir / "block.json"), block_dir, call_id, attempts[call_id], output


def labels(assessment):
    # Pilot 1 stored items/behavior_id; the assessor's decision-point output stores annotations/behavior.
    assessment = assessment or {}
    if "annotations" in assessment:
        return {x["behavior"]: x["label"] for x in assessment["annotations"]}
    return {x["behavior_id"]: x["label"] for x in assessment.get("items", [])}


NO_GAP_REASON = "Clearly performed at this decision point."


def no_gap(request):
    """Copy of a full-condition coach request whose assessment shows no gap (0/1 -> 2)."""
    new = copy.deepcopy(request)
    for item in new["payload"]["assessment"]["annotations"]:
        if item["label"] in (0, 1):
            item.update(label=2, reason=NO_GAP_REASON, unclear_rule="")
    return new


def summarize_no_gap(rows):
    def line(name, group):
        none = sum(r["replay"]["action"] == "none" for r in group)
        targets = collections.Counter(r["replay"]["target_behavior"] for r in group if r["replay"]["action"] == "exercise")
        return f"| {name} | {len(group)} | {none}/{len(group)} | " + ", ".join(f"{k}:{v}" for k, v in sorted(targets.items()))
    agree = [r for r in rows if r.get("without_assessment_action") == "none"]
    lines = ["# Coach no-gap check (full condition)", "",
             "Recorded full-condition coach requests re-sent with the same prompt, model and seed, except that "
             "every assessor label 0 or 1 is rewritten to 2. The messages are unchanged, and the prompt tells the "
             "coach to check the assessment against them. Original decisions: "
             + ", ".join(f"{k}:{v}" for k, v in sorted(collections.Counter(r["v1"]["action"] for r in rows).items())) + ".", "",
             "| blocks | n | none | exercise targets |", "|---|---|---|---|",
             line("all", rows),
             line("without_assessment coach also chose none on these messages", agree),
             line("without_assessment coach chose an exercise", [r for r in rows if r not in agree]), ""]
    return "\n".join(lines)


def summarize(rows):
    def stats(group, version):
        n = len(group)
        decisions = [r[version] for r in group]
        none = sum(d["action"] == "none" for d in decisions)
        chosen = [(d, r["assessor_labels"]) for d, r in zip(decisions, group) if d["action"] == "exercise"]
        gap = sum(lab.get(d["target_behavior"]) in (0, 1) for d, lab in chosen)
        two = sum(lab.get(d["target_behavior"]) == 2 for d, lab in chosen)
        targets = collections.Counter(d["target_behavior"] for d, _ in chosen)
        no_gap = [r for r in group if not any(v in (0, 1) for v in r["assessor_labels"].values())]
        none_when_no_gap = sum(r[version]["action"] == "none" for r in no_gap)
        return (f"{n} | {none} | {gap}/{len(chosen)} | {two}/{len(chosen)} | {none_when_no_gap}/{len(no_gap)} | "
                + ", ".join(f"{k}:{v}" for k, v in sorted(targets.items())))

    lines = ["# Coach prompt replay", "",
             "Same recorded inputs, only the system prompt differs. Gap = the assessor labeled the chosen "
             "behavior 0 or 1; label 2 = the exercise targets a behavior the assessor scored as performed. "
             "No-gap blocks = the assessor gave no 0 or 1 at all. The without_assessment coach never saw these "
             "labels, so its numbers measure agreement with the assessor, not instruction following.", ""]
    header = "| condition | prompt | n | none | targets gap | targets label 2 | none when no gap | targets |"
    for title, key in (("By condition", "condition"), ("By reporting group (all coached conditions)", "reporting_group")):
        lines += [f"## {title}", "", header.replace("condition", key, 1), "|---|---|---|---|---|---|---|---|"]
        for value in sorted({r[key] for r in rows}):
            group = [r for r in rows if r[key] == value]
            for version in ("v1", "replay"):
                lines.append(f"| {value} | {version} | {stats(group, version)} |")
        lines.append("")
    changed = sum(r["v1"]["action"] != r["replay"]["action"] or r["v1"].get("exercise_id") != r["replay"].get("exercise_id")
                  for r in rows)
    lines += [f"Decisions that changed: {changed}/{len(rows)}.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, help="replacement system prompt (default: keep the recorded one)")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/rq2-pilot/pilot.json")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--no-gap", action="store_true", help="full-condition no-gap check (see module docstring)")
    args = parser.parse_args()
    if not args.prompt and not args.no_gap:
        parser.error("--prompt is required unless --no-gap is given")

    model = ExperimentConfig.parse(read_json(args.config)).models["coach"]
    prompt_text = args.prompt.read_text(encoding="utf-8") if args.prompt else None
    other = {}  # (shard, block_id) -> without_assessment action, for the no-gap summary
    if args.no_gap:
        for shard, block, _, call_id, request, output in recorded_decisions(args.pilot):
            if call_id.split("/")[1] == "without_assessment":
                other[(shard.name, block["block_id"])] = parse_decision(output, request["payload"]["exercise_bank"])["action"]
    args.output.mkdir(parents=True, exist_ok=True)
    out_path = args.output / "decisions.jsonl"
    done = {}
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            done[row["call_id"]] = row
    adapter, lock = CommandAdapter(), threading.Lock()

    def replay(item):
        shard, block, block_dir, call_id, request, v1 = item
        new = no_gap(request) if args.no_gap else copy.deepcopy(request)
        if prompt_text is not None:
            new["system_prompt"], new["prompt_version"] = prompt_text, args.prompt.stem
        bank = request["payload"]["exercise_bank"]
        for attempt in range(3):
            try:
                response = adapter.generate(new, model)
                break
            except TransportError:
                if attempt == 2:
                    raise
        decision = parse_decision(response["output"], bank)
        assessment_path = block_dir / "assessment.json"
        row = {"call_id": call_id, "shard": shard.name, "block_id": block["block_id"],
               "condition": call_id.split("/")[1], "profile_id": block["profile_id"],
               "reporting_group": block["reporting_group"], "pair_id": block["pair_id"],
               "prompt_version": new["prompt_version"],
               "assessor_labels": labels(read_json(assessment_path) if assessment_path.exists() else None),
               "v1": parse_decision(v1, bank), "replay": decision, "usage": response["usage"]}
        if args.no_gap:
            row["sent_labels"] = labels(new["payload"]["assessment"])
            row["without_assessment_action"] = other.get((shard.name, block["block_id"]))
        with lock, out_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    todo = [item for item in recorded_decisions(args.pilot) if item[3] not in done
            and (not args.no_gap or item[3].split("/")[1] == "full")]
    print(f"{len(done)} done, {len(todo)} to replay", flush=True)
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        for future in concurrent.futures.as_completed([pool.submit(replay, item) for item in todo]):
            try:
                row = future.result()
                done[row["call_id"]] = row
            except (TransportError, ValidationError) as exc:
                failures += 1
                print(f"failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    rows = sorted(done.values(), key=lambda r: r["call_id"])
    (args.output / "summary.md").write_text(summarize_no_gap(rows) if args.no_gap else summarize(rows), encoding="utf-8")
    print(f"{len(rows)} decisions, {failures} failures; summary in {args.output / 'summary.md'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
