"""Build the two human review packets for an RQ2 pilot (gates in docs/rq2-preregistration-draft.md).

    python3 scripts/rq2_review_packets.py outputs/rq2-pilot-2 [--per-profile 4] [--per-behavior 20]

Writes <runs>/review/:
- fidelity/<profile>.md and fidelity/ratings_template.csv: uncoached pre-task transcripts
  (the block's shared pre-task, before any coaching) with the profile, for the
  profile-fidelity gate. Each reviewer fills a copy of the template independently.
- evaluator/items.md, items.jsonl, labels_template.csv: decision points for the
  evaluator-calibration gate, stratified by behavior x reporting group x phase, at most
  one behavior per record. Each item is the exact prefix the evaluator scored (dialogue
  up to the decision turn), with no condition, profile or label. Annotators label under
  codebook v0.2 independently and before any discussion.
- evaluator/key.private.csv: the unblinding key and the model labels. Do not share it
  with annotators. It is needed afterwards to compare labels with the evaluator.
Selection is seeded and uses no labels, so it cannot favor easy or agreeing cases.
"""

import argparse
import collections
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from adaptive_tutor.evaluation import evaluator_payload  # noqa: E402

BEHAVIORS = ("B1", "B2", "B3", "B4")
QUESTIONS = ("errors_match_gaps", "competence_possible", "not_compliant_or_formulaic")


def records(runs: Path):
    """Every scored task record with its unblinding context."""
    for block_path in sorted(runs.glob("shards/*/blocks/*/block.json")):
        shard = block_path.parents[2]
        block = json.loads(block_path.read_text(encoding="utf-8"))
        packets = [("pre", None, block.get("pre_packet"))]
        packets += [("post", c, b.get("packet")) for c, b in sorted(block["branches"].items())]
        for phase, condition, blind_id in packets:
            if not blind_id:
                continue
            packet = json.loads((shard / "blinded" / f"{blind_id}.json").read_text(encoding="utf-8"))
            score_path = shard / "scores" / f"{blind_id}.json"
            score = json.loads(score_path.read_text(encoding="utf-8")) if score_path.exists() else {}
            labels = {x["behavior_id"]: x["label"] for x in score.get("items", [])}
            assessment = {}
            if phase == "pre" and (block_path.parent / "assessment.json").exists():
                items = json.loads((block_path.parent / "assessment.json").read_text(encoding="utf-8"))["items"]
                assessment = {x["behavior_id"]: x["label"] for x in items}
            yield {"shard": shard.name, "block": block, "block_dir": block_path.parent, "phase": phase,
                   "condition": condition, "packet": packet, "evaluator": labels, "assessor": assessment}


def label_text(value):
    return "N/A" if value is None else str(value)


def fidelity(runs, out, per_profile, rng):
    folder = out / "fidelity"
    folder.mkdir(parents=True, exist_ok=True)
    by_profile = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in records(runs):
        if r["phase"] == "pre":
            by_profile[r["block"]["profile_id"]][r["block"]["pair_id"]].append(r)
    rows = []
    for profile, by_pair in sorted(by_profile.items()):
        for pair in by_pair.values():
            rng.shuffle(pair)
        chosen, pairs = [], sorted(by_pair)
        while len(chosen) < per_profile and any(by_pair.values()):  # round-robin over task pairs
            for pair in pairs:
                if by_pair[pair] and len(chosen) < per_profile:
                    chosen.append(by_pair[pair].pop())
        snapshot = json.loads((chosen[0]["block_dir"] / "pre.json").read_text(encoding="utf-8"))["snapshot"]
        md = [f"# {profile}: uncoached pre-tasks", "", "Profile given to the learner:", "", "```json",
              json.dumps(snapshot["background"], indent=2), "```", "",
              "For each transcript answer yes/no in your own copy of `ratings_template.csv`:",
              "1. errors_match_gaps: do its mistakes match the stated knowledge gaps and misconceptions?",
              "2. competence_possible: does it still do what this person knows how to do, where relevant?",
              "3. not_compliant_or_formulaic: is it free of unrealistic compliance and formulaic replies?", ""]
        for r in chosen:
            block = r["block"]
            md += [f"## block {block['block_id']} ({block['pair_id']}, form {block['orientation'][0]})", ""]
            md += [f"- **{m['message_id']} {m['actor']}**: {m['content']}" for m in r["packet"]["messages"]]
            md.append("")
            rows += [{"reviewer": "", "profile_id": profile, "block_id": block["block_id"], **{q: "" for q in QUESTIONS},
                      "notes": ""}]
        (folder / f"{profile}.md").write_text("\n".join(md), encoding="utf-8")
    with (folder / "ratings_template.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["reviewer", "profile_id", "block_id", *QUESTIONS, "notes"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def evaluator_sample(runs, out, per_behavior, rng):
    folder = out / "evaluator"
    folder.mkdir(parents=True, exist_ok=True)
    pool = [r for r in records(runs)]
    rng.shuffle(pool)
    used, chosen = set(), []
    for behavior in BEHAVIORS:
        strata = collections.defaultdict(list)
        for r in pool:
            if r["packet"]["decision_message_ids"].get(behavior):
                strata[r["block"]["reporting_group"], r["phase"]].append(r)
        picked, keys = [], sorted(strata)
        while len(picked) < per_behavior and any(strata.values()):  # round-robin over strata
            for key in keys:
                while strata[key] and strata[key][-1]["packet"]["blind_record_id"] in used:
                    strata[key].pop()
                if strata[key] and len(picked) < per_behavior:
                    r = strata[key].pop()
                    used.add(r["packet"]["blind_record_id"])
                    picked.append(r)
        chosen += [(behavior, r) for r in picked]
    rng.shuffle(chosen)
    items, md, key, template = [], ["# Evaluator calibration items", "",
          "Label the judged turn (marked ▶) for the named behavior under codebook v0.2 "
          "(`src/adaptive_tutor/rq1/rubrics/specification_verification_v02.md`): 2, 1, 0 or N/A, with an N/A reason "
          "(no_opportunity or insufficient_evidence) and a one-line reason. Work alone; do not discuss until both "
          "annotators are done.", ""], [], []
    for index, (behavior, r) in enumerate(chosen, 1):
        item_id = f"E{index:03d}"
        payload = evaluator_payload(r["packet"], behavior)
        # tutor-assess item format (the rubric version is chosen by the run, not the item).
        items.append({"item_id": item_id, "session_id": "rq2-calibration-" + item_id, "agent": "scripted",
                      **{k: v for k, v in payload.items() if k != "rubric_version"}})
        md += [f"## {item_id} · {behavior}", ""]
        for m in payload["messages"]:
            mark = "▶ " if m["turn_id"] == payload["target_turn_id"] else ""
            md.append(f"- {mark}**{m['turn_id']} {m['role']}**: {m['content']}")
        md.append("")
        block = r["block"]
        key.append({"item_id": item_id, "behavior": behavior, "shard": r["shard"],
                    "blind_record_id": r["packet"]["blind_record_id"], "block_id": block["block_id"],
                    "profile_id": block["profile_id"], "reporting_group": block["reporting_group"],
                    "pair_id": block["pair_id"], "phase": r["phase"], "condition": r["condition"] or "",
                    "evaluator_label": label_text(r["evaluator"].get(behavior)) if r["evaluator"] else "unscored",
                    "assessor_label": label_text(r["assessor"].get(behavior)) if r["assessor"] else ""})
        template.append({"item_id": item_id, "behavior": behavior, "annotator": "", "label": "", "na_reason": "",
                         "reason": ""})
    (folder / "items.md").write_text("\n".join(md), encoding="utf-8")
    (folder / "items.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                                        encoding="utf-8")
    for name, rows in (("key.private.csv", key), ("labels_template.csv", template)):
        with (folder / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return collections.Counter((b, r["block"]["reporting_group"], r["phase"]) for b, r in chosen)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    parser.add_argument("--per-profile", type=int, default=4)
    parser.add_argument("--per-behavior", type=int, default=20)
    parser.add_argument("--seed", type=int, default=329)
    args = parser.parse_args()
    out = args.runs / "review"
    n = fidelity(args.runs, out, args.per_profile, random.Random(args.seed))
    strata = evaluator_sample(args.runs, out, args.per_behavior, random.Random(args.seed + 1))
    print(f"fidelity: {n} transcripts; evaluator: {sum(strata.values())} items -> {out}")
    for (behavior, group, phase), count in sorted(strata.items()):
        print(f"  {behavior} {group} {phase}: {count}")


if __name__ == "__main__":
    main()
