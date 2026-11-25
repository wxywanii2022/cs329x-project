"""Pool the per-shard analysis exports of an RQ2 run into paired contrasts.

    python3 scripts/rq2_pooled_analysis.py <runs dir> [--pairs heldout_01 ...] [--resamples 10000]

Reads <runs>/shards/*/analysis/results.csv and behavior_scores.csv (written by each
runner). Units are run blocks: every contrast is a within-block difference of
post-task percentages (equal to the difference in gains, since the four branches
share one pre-task). Uncertainty is a two-stage percentile bootstrap: resample task
pairs, then blocks within each sampled pair, so a block's four branches always stay
together and task-pair clustering is respected. With few pairs the interval is
wide by design. Failed or unscored branches stay missing (counted by condition), and
are never treated as learner mistakes. Writes <runs>/pooled/analysis.{md,json}.
"""

import argparse
import collections
import csv
import json
import random
import statistics
from pathlib import Path

CONTRASTS = [("full", "no_coaching"), ("without_assessment", "no_coaching"), ("without_background", "no_coaching"),
             ("full", "without_assessment"), ("full", "without_background")]
BEHAVIORS = ("B1", "B2", "B3", "B4")


def number(value):
    return float(value) if value not in ("", None) else None


def load(runs: Path, pairs):
    blocks = {}
    for results in sorted(runs.glob("shards/*/analysis/results.csv")):
        with results.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if pairs and row["pair_id"] not in pairs:
                    continue
                block = blocks.setdefault(row["block_id"], {
                    "pair": row["pair_id"], "group": row["reporting_group"], "profile": row["profile_id"],
                    "pre": number(row["pre_percent"]), "post": {}, "status": {}, "coaching": {}, "labels": {}})
                block["post"][row["condition"]] = number(row["post_percent"])
                block["status"][row["condition"]] = (row["status"], row["score_status"])
                block["coaching"][row["condition"]] = row["coaching_status"]
        scores = results.parent / "behavior_scores.csv"
        if scores.exists():
            with scores.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    if row["block_id"] in blocks and row["phase"] == "post":
                        blocks[row["block_id"]]["labels"][row["condition"], row["behavior_id"]] = number(row["label"])
    return blocks


def estimate(blocks, value, resamples, seed):
    """Mean of value(block) over blocks where it is defined, with a pair-then-block bootstrap."""
    by_pair = collections.defaultdict(list)
    for block in blocks:
        v = value(block)
        if v is not None:
            by_pair[block["pair"]].append(v)
    values = [v for vs in by_pair.values() for v in vs]
    if not values:
        return {"n": 0, "pairs": 0, "mean": None, "ci95": None}
    interval = None
    if len(by_pair) >= 2:
        rng, pairs, means = random.Random(seed), sorted(by_pair), []
        for _ in range(resamples):
            sample = []
            for pair in rng.choices(pairs, k=len(pairs)):
                sample += rng.choices(by_pair[pair], k=len(by_pair[pair]))
            means.append(statistics.fmean(sample))
        means.sort()
        interval = [round(means[int(0.025 * resamples)], 2), round(means[int(0.975 * resamples) - 1], 2)]
    return {"n": len(values), "pairs": len(by_pair), "mean": round(statistics.fmean(values), 2), "ci95": interval}


def diff(a, b):
    return a - b if a is not None and b is not None else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    parser.add_argument("--pairs", nargs="*", help="Restrict to these task pairs (default: all)")
    parser.add_argument("--resamples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=329)
    args = parser.parse_args()
    blocks = list(load(args.runs, set(args.pairs or [])).values())
    groups = ["all"] + sorted({b["group"] for b in blocks})
    pick = lambda g: [b for b in blocks if g == "all" or b["group"] == g]
    report = {"blocks": len(blocks), "pairs": sorted({b["pair"] for b in blocks}), "contrasts": {}, "behaviors": {},
              "baseline": {}, "failures": {}, "coaching": {}}
    md = ["# RQ2 pooled paired analysis", "",
          f"{len(blocks)} blocks over task pairs {', '.join(report['pairs'])}. Contrasts are within-block differences "
          "of post-task percentage of available points (percentage points); 95% intervals are pair-then-block "
          f"percentile bootstraps ({args.resamples} resamples, seed {args.seed}).", ""]
    md += ["## Paired contrasts (pp)", "", "| group | " + " | ".join(f"{a} − {b}" for a, b in CONTRASTS) + " |",
           "|---|" + "---|" * len(CONTRASTS)]
    for g in groups:
        cells = []
        for a, b in CONTRASTS:
            result = estimate(pick(g), lambda x: diff(x["post"].get(a), x["post"].get(b)), args.resamples, args.seed)
            report["contrasts"][f"{g}:{a}-{b}"] = result
            cells.append(f"{result['mean']} {result['ci95'] or ''} (n={result['n']})")
        md.append(f"| {g} | " + " | ".join(cells) + " |")
    md += ["", "## Per-behavior post-task label difference, full − no_coaching", "",
           "| group | " + " | ".join(BEHAVIORS) + " |", "|---|" + "---|" * len(BEHAVIORS)]
    for g in groups:
        cells = []
        for behavior in BEHAVIORS:
            result = estimate(pick(g), lambda x: diff(x["labels"].get(("full", behavior)),
                                                     x["labels"].get(("no_coaching", behavior))), args.resamples, args.seed)
            report["behaviors"][f"{g}:{behavior}"] = result
            cells.append(f"{result['mean']} {result['ci95'] or ''} (n={result['n']})")
        md.append(f"| {g} | " + " | ".join(cells) + " |")
    md += ["", "## Baseline and operations", "",
           "| group | blocks | mean pre % | failed or unscored branches by condition | coaching status (coached conditions) |",
           "|---|---|---|---|---|"]
    for g in groups:
        rows = pick(g)
        pre = [b["pre"] for b in rows if b["pre"] is not None]
        failures = collections.Counter(c for b in rows for c, (status, score) in b["status"].items()
                                       if status != "complete" or score != "complete")
        coaching = collections.Counter(s for b in rows for c, s in b["coaching"].items() if c != "no_coaching")
        report["baseline"][g] = round(statistics.fmean(pre), 2) if pre else None
        report["failures"][g], report["coaching"][g] = dict(failures), dict(coaching)
        md.append(f"| {g} | {len(rows)} | {report['baseline'][g]} | {dict(failures) or 'none'} | {dict(coaching)} |")
    md += ["", "Descriptive within-sample estimates. Repeated model samples estimate stochastic variability, "
           "not a human population; few task pairs give limited task-level evidence.", ""]
    out = args.runs / "pooled"
    out.mkdir(exist_ok=True)
    (out / "analysis.md").write_text("\n".join(md), encoding="utf-8")
    (out / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
