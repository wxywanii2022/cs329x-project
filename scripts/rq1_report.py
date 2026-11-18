"""Summarize local-model RQ1 runs on Main 1 against A, B and the adjudicated reference.

  .venv/bin/python scripts/rq1_report.py --runs outputs/rq1 --data data/rq1/main60 \
      --save outputs/rq1/report

Expects outputs/rq1/<model-key>/main60-s<seed>/ from scripts/rq1_vllm.sbatch. Runs are
read through audit_run, so tampered or mismatched journals are rejected. Pre-declared
analysis: the primary run is --primary-seed; agreement is over successful pairs, with
failures reported separately (never counted as N/A); 95% percentile bootstrap over items;
the other seeds measure label stability, and a secondary majority-of-seeds label breaks
ties with the primary seed.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from adaptive_tutor.analysis import agreement  # noqa: E402
from adaptive_tutor.rq1.metrics import read_reference  # noqa: E402
from adaptive_tutor.rq1.pipeline import audit_run  # noqa: E402
from adaptive_tutor.storage import Journal, digest  # noqa: E402

LABELS = ["0", "1", "2", "N/A"]
QUOTE_ERRORS = {"Invalid exact evidence quote", "Evidence quote not in cited turn"}  # v1, v2 contracts


def load_run(path):
    frozen, results = audit_run(path)
    events = Journal.read(path / "events.jsonl")
    latency = {e["call_id"]: e["latency_ms"] for e in events if e["kind"] == "call_result"}
    contract = frozen.get("contract_version", "decision-point-v1")
    # Historical v1/v2 sensitivity only. Under v3 the opportunity check comes AFTER
    # quote validation, so a quote failure cannot be assumed otherwise valid.
    quote_only = {e["call_id"]: e["response"]["output"]["label"] for e in events
                  if contract in {"decision-point-v1", "decision-point-v2"}
                  and e["kind"] == "call_failure" and e["error"] in QUOTE_ERRORS}
    call_ids = {x["item_id"]: "rq1/" + digest(x["item_id"]) for x in frozen["items"]}
    labels, details, failures = {}, {}, {}
    for r in results:
        if r["status"] == "complete":
            a = r["annotation"]
            labels[r["item_id"]] = "N/A" if a["label"] is None else str(a["label"])
            details[r["item_id"]] = {"behavior": r["behavior"], "confidence": a["confidence"], "reason": a["reason"],
                                     "unclear_rule": a["unclear_rule"], "output_tokens": r["usage"]["output_tokens"]}
        else:
            failures[r["item_id"]] = r["error"]
    return {"model_id": frozen["model"]["model_id"], "seed": frozen["seed"], "model": frozen["model"],
            "budget": frozen["budget"], "contract": frozen.get("contract_version", "decision-point-v1"), "items": len(frozen["items"]), "pending": len(frozen["items"]) - len(results),
            "labels": labels, "details": details, "failures": failures,
            "quote_failed_labels": {k: "N/A" if quote_only[c] is None else str(quote_only[c])
                                    for k, c in call_ids.items() if k in failures and c in quote_only},
            "latency_s": [v / 1000 for v in latency.values()]}


def score(pairs):
    if not pairs:
        return {"n": 0, "raw_agreement": None, "cohen_kappa": None, "false_missed_rate": None,
                "false_missed_count": 0, "non_missed_reference_count": 0,
                "confusion": [[0] * len(LABELS) for _ in LABELS]}
    m = agreement([r for r, _ in pairs], [c for _, c in pairs])
    m["false_missed_rate"] = m["false_missed_count"] / m["non_missed_reference_count"] if m["non_missed_reference_count"] else None
    return m


def bootstrap(pairs, reps, seed):
    rng, draws = random.Random(seed), {k: [] for k in ("raw_agreement", "cohen_kappa", "false_missed_rate")}
    for _ in range(reps):
        m = score([pairs[rng.randrange(len(pairs))] for _ in pairs])
        for k in draws:
            if m[k] is not None:
                draws[k].append(m[k])
    def interval(xs):
        xs = sorted(xs)
        return [xs[int(0.025 * (len(xs) - 1))], xs[int(0.975 * (len(xs) - 1))]] if xs else None
    return {k: interval(v) for k, v in draws.items()}


def compare(reference, labels, ids=None):
    keys = [k for k in sorted(reference) if reference[k] and labels.get(k) and (ids is None or k in ids)]
    return [(reference[k], labels[k]) for k in keys]


def summary(reference, labels, reps, seed, behaviors=None):
    pairs = compare(reference, labels)
    out = {k: v for k, v in score(pairs).items() if k != "labels"}
    out["ci95"] = bootstrap(pairs, reps, seed) if pairs else None
    if behaviors:
        out["by_behavior"] = {b: {k: v for k, v in score(compare(reference, labels, {i for i in behaviors if behaviors[i] == b})).items()
                                  if k in ("n", "raw_agreement", "cohen_kappa", "false_missed_count")} for b in ("B1", "B2", "B3", "B4")}
    return out


def fmt(x, ci=None):
    if x is None:
        return "–"
    return f"{x:.3f}" + (f" [{ci[0]:.2f}, {ci[1]:.2f}]" if ci else "")


def fmt_fmr(metrics):
    ci = metrics.get("ci95")
    return (fmt(metrics["false_missed_rate"], ci and ci["false_missed_rate"])
            + f" ({metrics['false_missed_count']}/{metrics['non_missed_reference_count']})")


def high_confidence_zero_labels(run):
    """Secondary rule (c), derived from valid outputs only; never mutate journals."""
    return {k: "N/A" if label == "0" and run["details"][k]["confidence"] != "high" else label
            for k, label in run["labels"].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--save", type=Path, required=True, help="Path prefix for .json and .md")
    parser.add_argument("--primary-seed", type=int, default=329)
    parser.add_argument("--bootstrap", type=int, default=10000)
    args = parser.parse_args()
    if any(args.save.with_suffix(ext).exists() for ext in (".json", ".md")):
        parser.error("Report already exists; use a new --save prefix")

    refs = {name: read_reference(args.data / f"reference_{name}.csv") for name in ("adjudicated", "A", "B")}
    behaviors = {json.loads(line)["item_id"]: json.loads(line)["behavior"]
                 for line in (args.data / "items.jsonl").read_text(encoding="utf-8").split("\n") if line.strip()}
    ab_disagree = {k for k in refs["A"] if refs["A"][k] and refs["B"][k] and refs["A"][k] != refs["B"][k]}
    ab_agree = {k for k in refs["A"] if refs["A"][k] and refs["A"][k] == refs["B"][k]}
    report = {"primary_seed": args.primary_seed, "bootstrap_reps": args.bootstrap,
              "humans": {"A_vs_B": summary(refs["A"], refs["B"], args.bootstrap, 1),
                         "A_vs_adjudicated": summary(refs["adjudicated"], refs["A"], args.bootstrap, 1),
                         "B_vs_adjudicated": summary(refs["adjudicated"], refs["B"], args.bootstrap, 1)},
              "reference_distribution": dict(Counter(v for v in refs["adjudicated"].values())), "models": {}}

    for model_dir in sorted(p for p in args.runs.iterdir() if p.is_dir()):
        runs = {int(p.name.rsplit("-s", 1)[1]): load_run(p) for p in sorted(model_dir.glob("main60-s*"))
                if (p / "frozen_inputs.json").exists()}
        if args.primary_seed not in runs:
            continue
        if runs[args.primary_seed]["contract"] == "decision-point-v3":
            if set(runs) != {329, 330, 331} or any(r["pending"] for r in runs.values()):
                parser.error("v3 report requires all three completed seed runs (failed outcomes are retained)")
        model = {"model_id": runs[args.primary_seed]["model_id"], "model_spec": runs[args.primary_seed]["model"],
                 "budget": runs[args.primary_seed]["budget"], "contract": runs[args.primary_seed]["contract"], "seeds": {}}
        for seed, run in sorted(runs.items()):
            tokens = [d["output_tokens"] for d in run["details"].values()]
            model["seeds"][seed] = {
                "completed": len(run["labels"]), "failed": len(run["failures"]), "pending": run["pending"],
                "coverage": {"valid": len(run["labels"]), "total": run["items"],
                             "fraction": len(run["labels"]) / run["items"]},
                "failures": run["failures"], "label_distribution": dict(Counter(run["labels"].values())),
                "output_tokens_median": statistics.median(tokens) if tokens else None,
                "output_tokens_max": max(tokens) if tokens else None,
                "latency_s_median": statistics.median(run["latency_s"]) if run["latency_s"] else None,
                "quote_only_failures": len(run["quote_failed_labels"]),
                "posthoc_vs_adjudicated_with_quote_failures": summary(
                    refs["adjudicated"], {**run["labels"], **run["quote_failed_labels"]}, args.bootstrap, seed)
                    if run["contract"] in {"decision-point-v1", "decision-point-v2"} else None,
                **{f"vs_{name}": summary(ref, run["labels"], args.bootstrap, seed, behaviors if name == "adjudicated" else None)
                   for name, ref in refs.items()}}
        primary = runs[args.primary_seed]
        model["primary"] = {
            "vs_adjudicated_on_AB_agreed": {k: v for k, v in score(compare(refs["adjudicated"], primary["labels"], ab_agree)).items() if k != "labels"},
            "vs_adjudicated_on_AB_disagreed": {k: v for k, v in score(compare(refs["adjudicated"], primary["labels"], ab_disagree)).items() if k != "labels"},
            "disagreements": [{"item_id": k, "behavior": behaviors[k], "adjudicated": refs["adjudicated"][k], "A": refs["A"][k],
                               "B": refs["B"][k], "model": primary["labels"][k], **primary["details"][k]}
                              for k in sorted(primary["labels"]) if refs["adjudicated"].get(k) and primary["labels"][k] != refs["adjudicated"][k]]}
        if primary["contract"] == "decision-point-v3":
            model["primary"]["secondary_high_confidence_zero"] = {
                "coverage": {"valid": len(primary["labels"]), "total": primary["items"]},
                **{f"vs_{name}": summary(ref, high_confidence_zero_labels(primary), args.bootstrap, args.primary_seed)
                   for name, ref in refs.items()}}
            model["primary"]["v2_false_missed_followup"] = [
                {"item_id": k, "adjudicated": refs["adjudicated"].get(k),
                 "status": "complete" if k in primary["labels"] else "failed",
                 "label": primary["labels"].get(k), "error": primary["failures"].get(k)}
                for k in ("M1-005", "M1-027", "M1-034", "M1-035", "M1-040", "M1-044")
                if k in primary["labels"] or k in primary["failures"]]
        common = sorted(set.intersection(*(set(r["labels"]) for r in runs.values())))
        if len(runs) > 1 and common:
            seeds = sorted(runs)
            pairwise = [agreement([runs[a]["labels"][k] for k in common], [runs[b]["labels"][k] for k in common])["cohen_kappa"]
                        for i, a in enumerate(seeds) for b in seeds[i + 1:]]
            def majority(k):
                votes = Counter(runs[s]["labels"][k] for s in seeds).most_common()
                return votes[0][0] if len(votes) == 1 or votes[0][1] > votes[1][1] else runs[args.primary_seed]["labels"][k]
            model["stability"] = {"seeds": seeds, "items_completed_in_all": len(common),
                                  "unanimous": sum(len({runs[s]["labels"][k] for s in seeds}) == 1 for k in common),
                                  "unstable_items": [k for k in common if len({runs[s]["labels"][k] for s in seeds}) > 1],
                                  "mean_pairwise_kappa": statistics.mean(p for p in pairwise if p is not None) if any(p is not None for p in pairwise) else None,
                                  "majority_coverage": {"valid": len(common), "total": primary["items"]},
                                  "majority_vs_adjudicated": summary(refs["adjudicated"], {k: majority(k) for k in common}, args.bootstrap, 7)}
        report["models"][model_dir.name] = model

    args.save.parent.mkdir(parents=True, exist_ok=True)
    args.save.with_suffix(".json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    args.save.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))


def markdown(report):
    h, lines = report["humans"], []
    add = lines.append
    add("# RQ1 Main 1: local assessor vs human reference\n")
    add(f"Adjudicated reference: {report['reference_distribution']}. Agreement over successful pairs; "
        f"95% bootstrap intervals ({report['bootstrap_reps']} item resamples). Primary run = seed {report['primary_seed']}.\n")
    add("| Comparison | n | Raw agreement | Cohen's κ | False-missed rate |")
    add("|---|---|---|---|---|")
    for name, m in (("Human A vs B (pre-adjudication)", h["A_vs_B"]), ("Human A vs adjudicated", h["A_vs_adjudicated"]),
                    ("Human B vs adjudicated", h["B_vs_adjudicated"])):
        add(f"| {name} | {m['n']} | {fmt(m['raw_agreement'], m['ci95']['raw_agreement'])} | "
            f"{fmt(m['cohen_kappa'], m['ci95']['cohen_kappa'])} | {fmt_fmr(m)} |")
    for key, model in report["models"].items():
        for seed, s in model["seeds"].items():
            tag = "primary" if seed == report["primary_seed"] else "seed"
            for ref in ("adjudicated", "A", "B"):
                m = s[f"vs_{ref}"]
                add(f"| {key} s{seed} ({tag}) vs {ref} | {m['n']} | {fmt(m['raw_agreement'], m['ci95'] and m['ci95']['raw_agreement'])} | "
                    f"{fmt(m['cohen_kappa'], m['ci95'] and m['ci95']['cohen_kappa'])} | {fmt_fmr(m)} |")
    for key, model in report["models"].items():
        p = model["seeds"][report["primary_seed"]]
        add(f"\n## {key}\n\n`{model['model_id']}`; temperature {model['model_spec']['temperature']}; "
            f"command flags `{' '.join(model['model_spec'].get('command', [])[3:])}`; max output tokens {model['budget']['max_output_tokens']}; output contract {model['contract']}.\n")
        for seed, s in model["seeds"].items():
            add(f"- seed {seed}: coverage {s['completed']}/{s['completed'] + s['failed'] + s['pending']}, failed {s['failed']}, pending {s['pending']}, "
                f"labels {s['label_distribution']}, median output tokens {s['output_tokens_median']}, median latency {fmt(s['latency_s_median'])} s")
            if s["quote_only_failures"]:
                m = s["posthoc_vs_adjudicated_with_quote_failures"]
                add(f"  - post-hoc (not pre-declared), also scoring the {s['quote_only_failures']} outputs that failed only the exact-quote check: "
                    f"n {m['n']}, raw {fmt(m['raw_agreement'], m['ci95']['raw_agreement'])}, κ {fmt(m['cohen_kappa'], m['ci95']['cohen_kappa'])}, "
                    f"false-missed {fmt(m['false_missed_rate'], m['ci95']['false_missed_rate'])}")
            for reason, count in Counter(e.split(": ", 1)[-1][:120] for e in s["failures"].values()).most_common():
                add(f"  - {count} failed: {reason}")
        confusion = p["vs_adjudicated"]["confusion"]
        add("\nPrimary confusion (rows = adjudicated, columns = model):\n")
        add("| | " + " | ".join(LABELS) + " |"); add("|---" * 5 + "|")
        for label, row in zip(LABELS, confusion):
            add(f"| **{label}** | " + " | ".join(map(str, row)) + " |")
        add("\n| Behavior | n | Raw | κ | False-missed count |"); add("|---|---|---|---|---|")
        for b, m in p["vs_adjudicated"]["by_behavior"].items():
            add(f"| {b} | {m['n']} | {fmt(m['raw_agreement'])} | {fmt(m['cohen_kappa'])} | {m.get('false_missed_count', 0)} |")
        pa, pd = model["primary"]["vs_adjudicated_on_AB_agreed"], model["primary"]["vs_adjudicated_on_AB_disagreed"]
        add(f"\nOn items where A and B agreed: {pa['n']} items, raw {fmt(pa['raw_agreement'])}. "
            f"Where they disagreed: {pd['n']} items, raw {fmt(pd['raw_agreement'])}.")
        if "stability" in model:
            st = model["stability"]
            add(f"\nSeed stability ({st['seeds']}): {st['unanimous']}/{st['items_completed_in_all']} items unanimous; "
                f"mean pairwise κ {fmt(st['mean_pairwise_kappa'])}; unstable: {', '.join(st['unstable_items']) or 'none'}. "
                f"Majority-of-seeds vs adjudicated (secondary): raw {fmt(st['majority_vs_adjudicated']['raw_agreement'])}, "
                f"κ {fmt(st['majority_vs_adjudicated']['cohen_kappa'])}, false-missed {fmt_fmr(st['majority_vs_adjudicated'])}; "
                f"coverage {st['majority_coverage']['valid']}/{st['majority_coverage']['total']} (all seeds valid; ties use primary seed).")
        if "secondary_high_confidence_zero" in model["primary"]:
            secondary = model["primary"]["secondary_high_confidence_zero"]
            m = secondary["vs_adjudicated"]
            add(f"\nHigh-confidence-zero rule (secondary, valid outputs only): κ {fmt(m['cohen_kappa'])}, "
                f"false-missed {fmt_fmr(m)}; coverage {secondary['coverage']['valid']}/{secondary['coverage']['total']}.")
            add("\n| v2 false-missed item | Adjudicated | v3 primary outcome |"); add("|---|---|---|")
            for item in model["primary"]["v2_false_missed_followup"]:
                add(f"| {item['item_id']} | {item['adjudicated']} | {item['label'] if item['status'] == 'complete' else 'failed'} |")
        add("\n| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |"); add("|---" * 8 + "|")
        for d in model["primary"]["disagreements"]:
            add(f"| {d['item_id']} | {d['behavior']} | {d['adjudicated']} | {d['A'] or 'blank'} | {d['B'] or 'blank'} | "
                f"{d['model']} | {d['confidence']} | {d['reason'].replace('|', '/')} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
