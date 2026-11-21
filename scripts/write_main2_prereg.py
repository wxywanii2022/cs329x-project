"""Write outputs/rq1-main2/preregistration.json (refuses to overwrite). No model calls.

Run from the project root after both preflight records exist:
  .venv/bin/python scripts/write_main2_prereg.py --sampling-plan <plan> --selection-manifest <manifest>
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from adaptive_tutor.rq1.core import CONTRACT_V2, CONTRACT_V3

OUT = PROJECT / "outputs/rq1-main2"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def text_sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sampling-plan", type=Path, required=True)
    ap.add_argument("--selection-manifest", type=Path, required=True)
    args = ap.parse_args()
    dest = OUT / "preregistration.json"
    if dest.exists():
        raise SystemExit("Refusing to overwrite the Main 2 preregistration")
    local = json.loads((OUT / "preflight-local-bytes.json").read_text())
    tokens = json.loads((OUT / "preflight-tokens.json").read_text())
    assert local["passed"] and tokens["passed"], "Preflight did not pass"
    assert local["items_sha256"] == tokens["items_sha256"] == sha(PROJECT / "data/rq1/main2/items.jsonl")
    configs = sorted((PROJECT / "configs/main2").glob("assessment.*.json"))
    tracked = [".gitignore", "scripts/rq1_vllm_sc.sbatch", "scripts/preflight_main2.py", "scripts/write_main2_prereg.py",
               "scripts/rq1_report.py", "src/adaptive_tutor/adapters/base.py", "src/adaptive_tutor/adapters/local_vllm.py",
               "src/adaptive_tutor/rq1/core.py", "src/adaptive_tutor/rq1/pipeline.py", "src/adaptive_tutor/rq1/metrics.py",
               "src/adaptive_tutor/rq1/rubrics/specification_verification_v02.md",
               "data/rq1/main2/reference_A.csv", "data/rq1/main2/reference_B.csv",
               "data/rq1/main2/reference_adjudicated.csv", "data/rq1/main2/sampling-audit.json",
               "data/rq1/main2/SHA256SUMS", "outputs/rq1-main2/preflight-local-bytes.json",
               "outputs/rq1-main2/preflight-tokens.json", "tests/test_sc_job.py"] + \
              [str(c.relative_to(PROJECT)) for c in configs]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT, capture_output=True, text=True).stdout.strip()
    keys = [c.stem.removeprefix("assessment.") for c in configs]
    record = {
        "purpose": "RQ1 Main 2: session-held-out evaluation of frozen v3 (primary) against frozen v2 on 60 newly sampled, independently human-labeled decision points. Recorded before any Main 2 model call.",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "items_sha256": local["items_sha256"],
        "git_head": head,
        "git_head_meaning": "Base HEAD at record creation, not the commit containing this record; exact file contents are pinned below",
        "decided_by": "Yuan Tian (2026-11-20): common 300,000-byte request budget for every Main 2 config; symmetric run matrix v2+v3 x 27B+9B x seeds 329/330/331",
        "frozen_and_unchanged": {
            "rubric": "v0.2 (sha256 in pinned files)",
            "contract_v3_sha256": text_sha(CONTRACT_V3),
            "contract_v2_sha256": text_sha(CONTRACT_V2),
            "models_revisions_decoding_timeouts": "identical to configs/v2 and configs/v3",
            "v3_primary_rule": "option (a) from outputs/rq1-v3/preregistration.json: qwen38-27b-fp8 seed 329, raw valid output, no voting or confidence filtering",
        },
        "budget_amendment": {
            "max_context_bytes": 300000,
            "previous": 200000,
            "scope": "Every configs/main2 config (v2/v3, both models, all seeds). The only difference from configs/v2 and configs/v3.",
            "reason": "M2-046 (~290 KB) and M2-047 (~222 KB) requests exceed 200,000 bytes for both contracts; 300,000 admits all 60 items for both contracts. Chosen from input sizes only, not from labels or model output.",
            "main1": "Main 1 configs, failures (including M1-009) and metrics stay unchanged; no Main 1 rerun is authorized by this record.",
        },
        "sample": {
            "items": 60, "per_behavior": 15, "per_agent": 12, "per_agent_behavior": 3,
            "items_sha256": local["items_sha256"],
            "items_location": "Not tracked in Git (redacted, not guaranteed anonymous). Byte-identical to the annotators' evidence; copied to the cluster and checked against this hash by the sbatch main2 stage.",
            "sampling_plan_sha256": sha(args.sampling_plan),
            "selection_manifest_sha256": sha(args.selection_manifest),
            "enrichment": "B2-B4 target turns pass frozen lexical/structural opportunity proxies; B1 unscreened. Not a population-uniform sample.",
            "heldout": local["heldout"],
            "participants": "39 participants; 44 items from 23 unseen participants, 16 from 16 previously seen participants; at most 4 items per participant. Session-held-out, NOT participant-disjoint.",
        },
        "human_reference": {
            "process": "Two annotators (A, B) labeled all 60 independently under v0.2 without model suggestions. Raw agreement and kappa were computed before any discussion. The 9 disagreements were adjudicated by an anonymous third-party judge in two steps (independent label first, then blinded Rater X/Y view with per-row random order). The judge's texts were pasted to the coordinator, who stated the judge wrote them; workbooks were transcribed from those texts. Original A/B labels unchanged.",
            "A_vs_B": {"n": 60, "raw": 0.85, "kappa": 0.772, "raw_ci95": [0.75, 0.93], "kappa_ci95": [0.64, 0.90]},
            "adjudicated": {"agreed": 51, "adjudicated": 9, "distribution": {"2": 29, "N/A": 20, "0": 8, "1": 3}},
            "B_missing_confidence_note": "B's 4 initially blank confidence fields were filled by B before adjudication; labels unaffected.",
            "finalized_before_any_main2_model_call": True,
        },
        "run_matrix": {
            "stage": "main2", "output_root": "outputs/rq1-main2/<config-key>/main2-s<seed>/",
            "configs": keys, "seeds": [329, 330, 331],
            "jobs": [f"RUNS=outputs/rq1-main2 sbatch scripts/rq1_vllm_sc.sbatch configs/main2/assessment.{k}.json main2" for k in keys],
            "planned_item_outcomes": 720,
            "hardware": "SC jag-standard, 1x RTX 6000 Ada 48GB per job, same vLLM runtime and arguments as the v3 Main 1 runs",
        },
        "token_preflight": {
            "max_model_len": tokens["max_model_len"],
            "input_limit": tokens["max_model_len"] - 32768,
            "results": [{k: r[k] for k in ("config", "max_input_tokens", "argmax", "over_limit")} for r in tokens["token_window"]],
            "transformers_version": tokens.get("transformers_version"),
            "note": "Chat-templated system prompt + canonical payload with generation prompt and enable_thinking=True, pinned tokenizers from the offline HF cache; run on a compute node.",
        },
        "analysis": {
            "references": ["adjudicated (primary)", "A", "B"],
            "primary": "v3 qwen38-27b-fp8 seed 329 vs adjudicated; comparator v2 qwen38-27b-fp8 seed 329",
            "metrics": ["coverage = valid outputs / 60 with failure types", "raw agreement", "unweighted four-category Cohen kappa",
                        "FMR = valid predicted 0 with nonzero/N/A reference / valid predictions with nonzero/N/A reference (numerator/denominator shown)",
                        "reference-zero detection: valid predicted 0 among reference 0 (count/denominator)", "4x4 confusion matrix"],
            "intervals": "95% percentile item bootstrap, 10000 resamples, same method as Main 1; ignores participant clustering (disclosed)",
            "secondary": ["9B ablation, all seeds", "seeds 330/331 separately", "per-behavior agreement",
                          "common-valid v2/v3 comparison on items valid in both", "options (b) majority vote and (c) high-confidence-zero as defined in the v3 preregistration"],
            "separation": "Main 2 is reported separately; its FMR is never pooled with Main 1 (different sampling, opportunity-enriched).",
            "interpretation": "Lower FMR is read together with coverage and reference-zero detection; dropped failures alone are not improvement. No automatic RQ2 contract switch.",
        },
        "failure_policy": "Invalid, truncated or budget-rejected outputs stay failed; no repair, resampling, manual journal edit or conversion to N/A. Preemption interruptions are resumed only for pending calls with identical frozen inputs and recorded as incidents.",
        "incidents_and_deviations": [
            "Token preflight was first started on the SC login node, where it stalled on NFS reads; it was killed before producing output and rerun as a CPU-only Slurm job on a compute node.",
            "Byte preflight was run locally (no tokenizer needed).",
        ],
        "sha256": {p: sha(PROJECT / p) for p in tracked},
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x") as f:
        json.dump(record, f, indent=1, ensure_ascii=False)
    print(dest)


if __name__ == "__main__":
    main()
