"""Summarize an RQ2 live pilot for the learner-realism review (no model calls).

    python3 scripts/rq2_pilot_report.py outputs/rq2-pilot

Reads every simulator run under <runs>/shards/* (plus <runs>/smoke for status only)
and the fixture checks <runs>/fixtures-*/vs-fixtures.json. Writes:

    <runs>/report.md          tables for the team review
    <runs>/report.json        the same numbers, machine-readable
    <runs>/transcripts/*.md   every dialogue, one file per profile, for reading

The lexical flags are screening aids that point reviewers at transcripts; they are
not labels. Behavior labels come from the assessor (pre-task) and the blinded
evaluator. Development tasks and a handful of blocks per profile: nothing here is
an effect estimate.
"""
from __future__ import annotations

import collections
import csv
import itertools
import json
import re
import statistics
import sys
from pathlib import Path

BEHAVIORS = ("B1", "B2", "B3", "B4")
GROUPS = ("novice", "intermediate", "expert")
CONDITIONS = ("full", "without_assessment", "without_background", "no_coaching")
FLAGS = {
    # Persona/prompt leakage: a person would not talk about these.
    "meta_leak": r"\b(as an ai|language model|simulat\w*|initial[_ ]background|my (profile|habits|misconceptions?)|"
                 r"misconceptions?|novice|intermediate learner|expert learner|json|(request|review|correction) stage)\b",
    # Talking like the assistant rather than the user.
    "assistant_voice": r"^\s*(certainly|of course|absolutely|great question|i'd be happy to|"
                       r"here(?:'s| is) (?:the|a|your) (?:summary|draft|revised|updated))",
    # Numbers the learner cannot know at the request stage (it has no table).
    "invented_figure_at_request": None,
    "long_message": None,
}
WRONG = r"\b(wrong|incorrect|error|mistake|inaccurate|doesn'?t add up|does not add up|not right|isn'?t right|off\b|miscalculat\w*)"


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def percent_mentioned(text: str, value: float) -> bool:
    return bool(re.search(rf"(?<![\d.]){re.escape(f'{value:g}')}(?:\.0+)?\s*(?:%|percent|per cent)", text, re.I))


def invented_figure(text: str) -> bool:
    text = re.sub(r"\b(q|quarter)\s*[1-4]\b", " ", text, flags=re.I)
    if re.search(r"\d\s*%", text):
        return True
    return any(int(n) >= 20 for n in re.findall(r"(?<![\d.])(\d+)(?![\d.])(?!\s*(?:words?|characters?|minutes?|seconds?|lines?))", text))


def flags_for(text: str, stage: str) -> list[str]:
    found = [name for name, pattern in FLAGS.items() if pattern and re.search(pattern, text, re.I)]
    if stage == "request" and invented_figure(text):
        found.append("invented_figure_at_request")
    if words(text) > 120:
        found.append("long_message")
    return found


def kappa(pairs):
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not pairs:
        return None, 0
    labels = sorted({x for p in pairs for x in p})
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    expected = sum(ca[x] * cb[x] for x in labels) / (n * n)
    return (None if expected == 1 else (observed - expected) / (1 - expected)), n


def lab(item) -> str:
    return "N/A" if item["label"] is None else str(item["label"])


def label_map(items) -> dict:
    return {x["behavior_id"]: lab(x) for x in items or []}


def mean(values):
    values = [v for v in values if v is not None]
    return round(statistics.mean(values), 3) if values else None


def rate(values):
    values = [bool(v) for v in values if v is not None]
    return f"{sum(values)}/{len(values)}" if values else "–"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join("–" if c is None else str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def load_run(run: Path) -> dict:
    frozen = load(run / "frozen_inputs.json") or {}
    tasks = {(t["pair_id"], t["form_id"]): t for t in frozen.get("tasks", [])}
    blocks = []
    for path in sorted(run.glob("blocks/*/block.json")):
        block = load(path)
        directory = path.parent
        pre = load(directory / "pre.json")
        block["pre"] = pre["record"] if pre else None
        block["background"] = pre["snapshot"]["background"] if pre else None
        block["assessment"] = load(directory / "assessment.json")
        block["pre_scores"] = load(run / "scores" / f"{block.get('pre_packet')}.json") if block.get("pre_packet") else None
        for condition, summary in block["branches"].items():
            result = load(directory / "branches" / condition / "result.json") or {}
            summary["result"] = result
            summary["scores"] = load(run / "scores" / f"{result.get('packet')}.json") if result.get("packet") else None
        block["tasks"] = (tasks.get((block["pair_id"], block["orientation"][0])),
                          tasks.get((block["pair_id"], block["orientation"][1])))
        blocks.append(block)
    calls = collections.defaultdict(list)
    failures = collections.Counter()
    transport = collections.Counter()
    journal = run / "events.jsonl"
    if journal.exists():
        with journal.open(encoding="utf-8") as handle:
            for line in handle:
                event = json.loads(line)
                if event["kind"] == "call_result":
                    calls[event["actor"]].append((event["latency_ms"], event["usage"]["output_tokens"]))
                elif event["kind"] == "call_failure":
                    failures[(event["actor"], str(event["error"])[:160])] += 1
                elif event["kind"] == "transport_failure":
                    transport[event["actor"]] += 1
    return {"run": run, "manifest": load(run / "manifest.json"), "audit": load(run / "audit.json"),
            "blocks": blocks, "calls": calls, "failures": failures, "transport": transport}


def learner_turns(record):
    return [m for m in record["messages"] if m["actor"] == "learner"]


def pre_metrics(block) -> dict | None:
    record, task = block["pre"], block["tasks"][0]
    if not record or not task or task["error_schedule"]["kind"] not in {"incorrect_growth", "accurate"}:
        return None
    turns = learner_turns(record)
    if len(turns) < 3:
        return None
    request, review, correction = (t["content"] for t in turns[:3])
    correct = task["private_answer_key"]["growth_percent"]
    claimed = task["error_schedule"]["claimed_percent"]
    incorrect = task["error_schedule"]["kind"] == "incorrect_growth"
    flags = sorted({f for text, stage in ((request, "request"), (review, "review"), (correction, "correction"))
                    for f in flags_for(text, stage)})
    return {
        "kind": task["error_schedule"]["kind"],
        "request_words": words(request), "review_words": words(review), "correction_words": words(correction),
        "spontaneous_check": record["discovery"] == "spontaneous" if incorrect else None,
        "states_correct_at_review": percent_mentioned(review, correct) if incorrect else None,
        "names_claim_at_review": percent_mentioned(review, claimed),
        "early_correction": record["b4_decision_stage"] == "review" if incorrect else None,
        "final_correct": record["mechanical_checks"]["arithmetic_correct"],
        "false_alarm_at_review": bool(re.search(WRONG, review, re.I)) if not incorrect else None,
        "asks_evidence_at_request": bool(re.search(r"source|calculat|show (?:the |your )?(?:math|work)|cite|citation|how (?:you|it was) (?:got|computed|calculated)", request, re.I)),
        "flags": flags,
        "request": request,
    }


def similarity(texts):
    sets = [set(re.findall(r"\b\w+\b", t.lower())) for t in texts]
    pairs = [len(a & b) / len(a | b) for a, b in itertools.combinations(sets, 2) if a | b]
    return round(statistics.mean(pairs), 2) if pairs else None


def transcript(block) -> str:
    lines = [f"## {block['profile_id']} · {block['pair_id']} · {block['orientation']} · rep {block['replicate']} (block {block['block_id']})", ""]
    record = block["pre"]
    if not record:
        return "\n".join(lines + [f"Pre-task failed: {block.get('error')}", ""])
    def dialogue(messages):
        return [f"- **{m['message_id']} {m['actor']}**: " + m["content"].replace("\n", " ⏎ ") for m in messages]
    lines += ["### Pre-task", *dialogue(record["messages"]), ""]
    assess = block["assessment"]
    if assess:
        lines += ["Assessor: " + "; ".join(f"{a['behavior']}={'N/A' if a['label'] is None else a['label']} ({a['reason']})"
                                         for a in assess["annotations"]), ""]
    else:
        lines += [f"Assessor failed: {block.get('assessment_error')}", ""]
    if block["pre_scores"] and block["pre_scores"].get("status") == "complete":
        lines += ["Evaluator: " + "; ".join(f"{x['behavior_id']}={lab(x)} ({x['brief_rationale']})" for x in block["pre_scores"]["items"]), ""]
    for condition in block.get("execution_order", CONDITIONS):
        branch = block["branches"].get(condition, {})
        result = branch.get("result") or {}
        lines.append(f"### {condition} — {branch.get('status')}")
        if result.get("error") or branch.get("error"):
            lines.append(f"Error: {result.get('error') or branch.get('error')}")
        decision = result.get("decision")
        if decision:
            lines.append(f"Coach: {decision['action']} {decision.get('exercise_id') or ''} — {decision['brief_rationale']}"
                         f" (status {result.get('coaching_status')}, turns {result.get('coaching_turns')})")
        post = result.get("record")
        state = result.get("final_state")
        if state and post:
            coaching = state["messages"][len(record["messages"]):len(state["messages"]) - len(post["messages"])]
            if coaching:
                lines += ["Coaching:", *dialogue(coaching)]
        if post:
            lines += ["Post-task:", *dialogue(post["messages"])]
        scores = branch.get("scores")
        if scores and scores.get("status") == "complete":
            lines.append("Evaluator: " + "; ".join(f"{x['behavior_id']}={lab(x)}" for x in scores["items"]))
        lines.append("")
    return "\n".join(lines)


def main(argv) -> int:
    root = Path(argv[1] if len(argv) > 1 else "outputs/rq2-pilot")
    runs = [load_run(p) for p in sorted((root / "shards").glob("*")) if p.is_dir()]
    smoke = load_run(root / "smoke") if (root / "smoke").is_dir() else None
    blocks = [b for r in runs for b in r["blocks"]]
    report = {"runs": [], "fixtures": {}, "learner": {}, "coach": {}, "agreement": {}, "operations": {}}
    md = [f"# RQ2 live pilot report", "",
          f"Runs: {len(runs)} shards, {len(blocks)} blocks with block.json. Development tasks only; screening "
          "flags are lexical pointers to transcripts, not labels; nothing here is an effect estimate.", ""]

    # Run status
    rows = []
    for r in ([smoke] if smoke else []) + runs:
        m = r["manifest"] or {}
        rows.append([r["run"].name, len(r["blocks"]), m.get("failed_branches"), m.get("failed_scores"),
                     (r["audit"] or {}).get("status", "not audited"), sum(r["failures"].values()), sum(r["transport"].values())])
        report["runs"].append(dict(zip(["run", "blocks", "failed_branches", "failed_scores", "audit", "call_failures", "transport_failures"], rows[-1])))
    md += ["## Run status", "", table(["run", "blocks", "failed branches", "failed scores", "audit", "call failures", "transport retries"], rows), ""]

    # Operations
    calls = collections.defaultdict(list)
    failures = collections.Counter()
    for r in runs:
        for actor, values in r["calls"].items():
            calls[actor] += values
        failures.update(r["failures"])
    rows = []
    for actor in ("learner", "assessment", "coach", "evaluator"):
        values = calls.get(actor, [])
        rows.append([actor, len(values), statistics.median(v[0] for v in values) / 1000 if values else None,
                     round(statistics.mean(v[1] for v in values)) if values else None, max((v[1] for v in values), default=None)])
    report["operations"] = {"per_role": rows, "failures": [[a, e, n] for (a, e), n in failures.most_common()]}
    md += ["## Calls per role", "", table(["role", "accepted calls", "median latency s", "mean output tokens", "max output tokens"], rows), ""]
    if failures:
        md += ["Call failures:", "", table(["role", "error", "count"], [[a, e, n] for (a, e), n in failures.most_common(20)]), ""]

    # Fixtures
    rows = []
    for path in sorted(root.glob("fixtures-*/vs-fixtures.json")):
        result = load(path)
        overall = result["overall"]
        disagreements = ", ".join(f"{d['item_id']} {d['behavior']} ref {d['reference']}→{d['candidate']}" for d in result["disagreements"])
        failed = result.get("failed_predictions") or 0  # a count (rq1.metrics), not a list
        rows.append([path.parent.name, overall.get("n"), round(overall["raw_agreement"], 3) if overall.get("raw_agreement") is not None else None,
                     round(overall["cohen_kappa"], 3) if overall.get("cohen_kappa") is not None else None,
                     overall.get("false_missed_count"), failed, disagreements or "none"])
        report["fixtures"][path.parent.name] = {"overall": {k: v for k, v in overall.items() if not isinstance(v, list)},
                                                "disagreements": result["disagreements"], "failed": failed}
    if rows:
        md += ["## v0.2 fixtures (constructed items; not an accuracy estimate; taskv2 = 5 learner-view-v2 items, others = 13)", "",
               table(["run", "n", "raw", "κ", "false-missed", "failed", "disagreements"], rows), ""]

    # Learner realism on uncoached pre-tasks
    metrics = [(b, pre_metrics(b)) for b in blocks]
    metrics = [(b, m) for b, m in metrics if m]
    md += ["## Learner behavior on the uncoached pre-task", "",
           "One row per profile; pre-tasks are shared by the block's four branches. Spontaneous check = the "
           "scripted agent recognized a targeted check of the draft before the disclosure; states correct = the "
           "review message itself gives the correct growth figure; early correction = named the error and asked "
           "for a fix at review; final correct = the final artifact's figure matches the table.", ""]
    rows = []
    for profile in sorted({b["profile_id"] for b, _ in metrics}, key=lambda p: (GROUPS.index(p.split("_")[0]) if p.split("_")[0] in GROUPS else 9, p)):
        mine = [(b, m) for b, m in metrics if b["profile_id"] == profile]
        wrong = [m for _, m in mine if m["kind"] == "incorrect_growth"]
        accurate = [m for _, m in mine if m["kind"] == "accurate"]
        flags = collections.Counter(f for _, m in mine for f in m["flags"])
        row = [profile, len(mine), rate(m["spontaneous_check"] for m in wrong), rate(m["states_correct_at_review"] for m in wrong),
               rate(m["early_correction"] for m in wrong), rate(m["final_correct"] for m in wrong),
               rate(m["false_alarm_at_review"] for m in accurate), rate(m["asks_evidence_at_request"] for _, m in mine),
               mean([m["request_words"] for _, m in mine]), mean([m["review_words"] for _, m in mine]),
               similarity([m["request"] for _, m in mine if m["kind"] == "incorrect_growth"]),
               ", ".join(f"{k}×{v}" for k, v in flags.most_common()) or "none"]
        rows.append(row)
        report["learner"][profile] = dict(zip(["profile", "pre_tasks", "spontaneous_check", "states_correct_at_review", "early_correction",
                                               "final_correct", "false_alarm_on_accurate", "asks_evidence_at_request", "request_words",
                                               "review_words", "request_similarity", "flags"], row))
    md += [table(["profile", "pre-tasks", "spontaneous check", "states correct", "early correction", "final correct",
                  "false alarm (accurate)", "asks evidence", "request words", "review words", "request similarity", "flags"], rows), ""]

    # Labels by reporting group (pre-task), assessor and evaluator
    rows = []
    for source in ("assessor", "evaluator"):
        for group in GROUPS:
            mine = [b for b, m in metrics if b["reporting_group"] == group and m["kind"] == "incorrect_growth"]
            labels = [label_map((b["assessment"] or {}).get("items")) if source == "assessor" else
                      label_map((b["pre_scores"] or {}).get("items") if (b["pre_scores"] or {}).get("status") == "complete" else None)
                      for b in mine]
            cells = []
            for behavior in BEHAVIORS:
                counts = collections.Counter(l.get(behavior, "missing") for l in labels)
                cells.append(" ".join(f"{k}:{counts[k]}" for k in ("2", "1", "0", "N/A", "missing") if counts[k]))
            rows.append([source, group, len(mine), *cells])
    report["learner"]["labels_by_group"] = rows
    md += ["### Pre-task labels by reporting group (briefs/incorrect-growth tasks)", "",
           "Counts of 2/1/0/N/A. Look for overlapping but different patterns, not a perfect ranking.", "",
           table(["labels from", "group", "pre-tasks", *BEHAVIORS], rows), ""]

    # Assessor vs evaluator on the same pre-task decision points
    pairs = collections.defaultdict(list)
    for b, _ in metrics:
        a = label_map((b["assessment"] or {}).get("items"))
        e = label_map((b["pre_scores"] or {}).get("items") if (b["pre_scores"] or {}).get("status") == "complete" else None)
        for behavior in BEHAVIORS:
            if behavior in a and behavior in e:
                pairs[behavior].append((a[behavior], e[behavior]))
                pairs["all"].append((a[behavior], e[behavior]))
    rows = []
    for key in (*BEHAVIORS, "all"):
        k, n = kappa(pairs[key])
        agree = sum(x == y for x, y in pairs[key])
        rows.append([key, n, f"{agree}/{n}" if n else None, None if k is None else round(k, 3)])
    report["agreement"] = rows
    md += ["### Assessor (Qwen v2) vs evaluator on the same pre-task decision points", "",
           "Two different models applying the same codebook; agreement is not accuracy.", "",
           table(["behavior", "n", "exact agreement", "κ"], rows), ""]

    # Coaching
    decisions = collections.Counter()
    statuses = collections.Counter()
    targeted = collections.Counter()
    practice = []
    for b in blocks:
        gaps = {k for k, v in label_map((b["assessment"] or {}).get("items")).items() if v in {"0", "1"}}
        for condition in CONDITIONS[:3]:
            result = b["branches"].get(condition, {}).get("result") or {}
            decision = result.get("decision")
            if not decision:
                continue
            decisions[(condition, decision.get("exercise_id") or "none")] += 1
            statuses[(condition, result.get("coaching_status"))] += 1
            if decision["action"] == "exercise":
                targeted[(condition, decision["target_behavior"] in gaps)] += 1
            state, post = result.get("final_state"), result.get("record")
            if state and post and b["pre"]:
                coaching = state["messages"][len(b["pre"]["messages"]):len(state["messages"]) - len(post["messages"])]
                practice += [words(m["content"]) for m in coaching if m["actor"] == "learner"]
    options = sorted({o for _, o in decisions})
    rows = [[c, *[decisions[(c, o)] for o in options],
             f"{targeted[(c, True)]}/{targeted[(c, True)] + targeted[(c, False)]}",
             ", ".join(f"{s}×{n}" for (cc, s), n in sorted(statuses.items(), key=str) if cc == c)] for c in CONDITIONS[:3]]
    report["coach"] = {"decisions": {f"{c}/{o}": n for (c, o), n in decisions.items()},
                       "practice_reply_words_mean": mean(practice)}
    md += ["## Coaching decisions", "",
           "Targets assessor gap = the chosen exercise's behavior was labeled 0 or 1 by the pre-task assessor "
           "(the without_assessment coach never saw those labels).", "",
           table(["condition", *options, "targets assessor gap", "coaching status"], rows), "",
           f"Learner practice replies: {len(practice)}, mean {mean(practice)} words.", ""]

    # Post vs pre, descriptive
    sums = collections.defaultdict(list)
    for r in runs:
        path = r["run"] / "analysis" / "results.csv"
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    if row["pair_id"] == "briefs_01" and row["gain_pp"] not in ("", None):
                        sums[(row["reporting_group"], row["condition"])].append(float(row["gain_pp"]))
    rows = [[g, *[f"{mean(sums[(g, c)])} (n={len(sums[(g, c)])})" if sums[(g, c)] else None for c in CONDITIONS]] for g in GROUPS]
    md += ["## Post-minus-pre gain (briefs_01, evaluator, percentage points; descriptive only)", "",
           table(["group", *CONDITIONS], rows), ""]

    # Transcripts and a few request examples
    out = root / "transcripts"
    out.mkdir(exist_ok=True)
    for profile in sorted({b["profile_id"] for b in blocks}):
        mine = sorted((b for b in blocks if b["profile_id"] == profile), key=lambda b: (b["pair_id"], b["orientation"], b["replicate"]))
        (out / f"{profile}.md").write_text(f"# {profile} transcripts\n\nBackground given to the learner:\n\n```json\n"
                                           + json.dumps(mine[0]["background"], indent=2) + "\n```\n\n"
                                           + "\n".join(transcript(b) for b in mine), encoding="utf-8")
    md += ["## Transcripts", "", f"Every dialogue is in `{out.relative_to(root)}/<profile>.md`.", ""]
    (root / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (root / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {root / 'report.md'} and {len(list(out.glob('*.md')))} transcript files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
