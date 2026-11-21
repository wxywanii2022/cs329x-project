"""Main 2 secondary metrics not in rq1_report.py: reference-zero detection and the paired
common-valid v2/v3 comparison (same model, same seed). Reads runs via rq1_report.load_run (audited).
  PYTHONPATH=src .venv/bin/python scripts/main2_extra_metrics.py > outputs/rq1-main2/extra_metrics.json
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rq1_report import load_run, score, compare  # noqa: E402
from adaptive_tutor.rq1.metrics import read_reference  # noqa: E402

P = Path(__file__).resolve().parents[1]
refs = {n: read_reference(P / f"data/rq1/main2/reference_{n}.csv") for n in ("adjudicated", "A", "B")}
out = {}
for model in ("qwen38-27b-fp8", "qwen35-9b"):
    for seed in (329, 330, 331):
        runs = {c: load_run(P / f"outputs/rq1-main2/{c}.{model}/main2-s{seed}") for c in ("v2", "v3")}
        row = {}
        for c, r in runs.items():
            for n, ref in refs.items():
                zeros = [k for k, v in ref.items() if v == "0"]
                row[f"{c}_vs_{n}_zero_detection"] = {
                    "detected": sum(r["labels"].get(k) == "0" for k in zeros),
                    "failed": sum(k in r["failures"] for k in zeros), "reference_zeros": len(zeros)}
        common = set(runs["v2"]["labels"]) & set(runs["v3"]["labels"])
        ref = refs["adjudicated"]
        m = {c: {k: v for k, v in score(compare(ref, runs[c]["labels"], common)).items() if k != "labels"} for c in runs}
        v2ok = {k for k in common if runs["v2"]["labels"][k] == ref[k]}
        v3ok = {k for k in common if runs["v3"]["labels"][k] == ref[k]}
        row["common_valid"] = {"n": len(common),
            **{c: {"raw": m[c]["raw_agreement"], "kappa": m[c]["cohen_kappa"],
                   "fmr": f"{m[c]['false_missed_count']}/{m[c]['non_missed_reference_count']}"} for c in m},
            "only_v2_correct": sorted(v2ok - v3ok), "only_v3_correct": sorted(v3ok - v2ok)}
        out[f"{model}/s{seed}"] = row
print(json.dumps(out, indent=1))
