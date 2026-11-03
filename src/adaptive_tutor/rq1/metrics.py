"""Post-run comparisons only. Never imported into model request construction."""
import csv
from pathlib import Path
from ..analysis import agreement
from ..schema import require
from .pipeline import audit_run


def read_reference(path):
    result = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        require({"item_id", "label"} <= set(reader.fieldnames or []), "Reference requires item_id,label columns")
        for row in reader:
            key, label = row["item_id"], row["label"].strip()
            require(bool(key) and key not in result, "Empty or duplicate reference item ID")
            require(label in {"", "0", "1", "2", "N/A"}, "Invalid reference label; blank is unfinished")
            result[key] = label or None
    require(bool(result), "Empty reference")
    return result


def metrics(left, right):
    if not left:
        return {"n": 0, "raw_agreement": None, "cohen_kappa": None,
                "false_missed_count": 0, "non_missed_reference_count": 0, "false_missed_rate": None}
    result = agreement(left, right)
    denominator = result["non_missed_reference_count"]
    result["false_missed_rate"] = result["false_missed_count"] / denominator if denominator else None
    result["false_missed_definition"] = "candidate=0 among paired successful items with reference in {1,2,N/A}"
    return result


def evaluate(output, reference, provenance="unspecified", revalidate=False):
    frozen, results = audit_run(output, revalidate)
    refs = read_reference(reference)
    source = {x["item_id"]: x for x in frozen["items"]}
    require(set(refs) <= source.keys(), "Reference contains IDs outside this run")
    candidates = {r["item_id"]: r for r in results}
    paired, disagreements = [], []
    for key, label in refs.items():
        result = candidates.get(key)
        if label is None or result is None or result["status"] != "complete":
            continue
        annotation = result["annotation"]
        prediction = "N/A" if annotation["label"] is None else str(annotation["label"])
        row = {"item_id": key, "behavior": result["behavior"], "reference": label, "candidate": prediction}
        paired.append(row)
        if label != prediction:
            disagreements.append(row)
    def score(rows):
        return metrics([r["reference"] for r in rows], [r["candidate"] for r in rows])
    return {"reference_provenance": provenance, "reference_rows": len(refs),
            "unlabeled_reference_rows": sum(v is None for v in refs.values()),
            "run_items_without_reference_row": len(set(source) - set(refs)),
            "failed_predictions": sum(r["status"] == "failed" for r in results),
            "revalidated_failures": [r["item_id"] for r in results if "revalidated_from_error" in r],
            "pending_predictions": len(source) - len(results),
            "labeled_references_without_successful_prediction": sum(v is not None and (k not in candidates or candidates[k]["status"] != "complete") for k,v in refs.items()),
            "overall": score(paired),
            "by_behavior": {b: score([r for r in paired if r["behavior"] == b]) for b in ("B1", "B2", "B3", "B4")},
            "disagreements": disagreements, "rubric_version": frozen["rubric_version"],
            "interpretation": "Agreement, not automatic ground-truth accuracy. Reference provenance is caller-declared. Model-assisted/development comparisons are exploratory. Missing and failed predictions never become N/A labels."}


def compare_humans(left, right):
    a, b = read_reference(left), read_reference(right)
    require(a.keys() == b.keys(), "Compare identical item sets before discussion/adjudication")
    paired = [k for k in a if a[k] is not None and b[k] is not None]
    return {"total_items": len(a), "jointly_labeled": len(paired),
            "incomplete_pairs": len(a) - len(paired), "agreement": metrics([a[k] for k in paired], [b[k] for k in paired]),
            "independence_verified": False,
            "note": "The command cannot establish rater independence. Keep original A/B and adjudicated files separate; never infer adjudication from agreement."}
