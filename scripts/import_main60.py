"""Convert the Main 1 annotation round into tutor-assess inputs and reference CSVs.

Inputs stay outside the repository: released source prefixes, the selection
manifest, the published packets (items.json) and the annotation workbook. The
packet builder's Redactor is loaded without running that script, and every
converted item is re-rendered and checked byte-for-byte against the packet the
human annotators saw. Reference labels are written to separate files and never
enter items.jsonl.

uv run --with openpyxl python scripts/import_main60.py \
  --research ../personalized_collaboration_research \
  --workbook ../annotation_workbook_副本.xlsx --output data/rq1/main60
"""
import argparse
import ast
import csv
import hashlib
import json
import re
from pathlib import Path

ROLES = {"user", "assistant", "tool", "system"}


def load_builder(builder):
    """Take Redactor and the packet header from the builder without running it."""
    tree = ast.parse(builder.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Redactor")
    namespace = {"re": re, "Counter": __import__("collections").Counter}
    exec(compile(ast.Module([node], []), str(builder), "exec"), namespace)
    header = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "header")
    return namespace["Redactor"], ast.literal_eval(header.value)


def convert(research, out):
    base = research / "annotation_main60"
    redactor_cls, header = load_builder(research / "scripts" / "build_main60_packets.py")
    manifest = json.loads((base / "selection_manifest.json").read_text(encoding="utf-8"))
    packets = {x["item_id"]: x for x in json.loads((base / "items.json").read_text(encoding="utf-8"))}
    rows = []
    for x in manifest["items"]:
        records = json.loads((base / "source_prefixes" / f"{x['item_id']}.json").read_text(encoding="utf-8"))
        assert records[-1]["turn_id"] == x["turn_id"]
        redactor = redactor_cls("\n".join(r.get("content", "") for r in records))
        messages, blocks = [], []
        for r in records:
            text = r.get("content", "")
            if not text.strip() or (r.get("role") == "user" and text.strip().startswith("/")):
                continue
            text = redactor.clean(text)
            role = (r.get("role") or "unclassified").upper()
            marked = "USER TO JUDGE — " if r is records[-1] else ""
            blocks.append(f"{marked}TURN {r['turn_id']} | {role} | {r.get('type') or 'record'}\n{text}\n\n")
            messages.append({"turn_id": str(r["turn_id"]),
                             "role": r["role"] if r.get("role") in ROLES else "evidence", "content": text})
        # Same rendering as build_main60_packets.py: proves identical evidence.
        full = header + f"Item: {x['item_id']} | Assigned behavior: {x['behavior']} | Target turn: {x['turn_id']}\n\n" + "".join(blocks)
        parts = [full[j:j + 5500] for j in range(0, len(full), 5500)]
        full = "\n\n".join(f"BEGIN EVIDENCE PART {j}/{len(parts)}\n{p}\nEND EVIDENCE PART {j}/{len(parts)}"
                           for j, p in enumerate(parts, 1))
        assert full == packets[x["item_id"]]["context"], f"{x['item_id']}: evidence differs from annotated packet"
        assert not re.search(r"\bsk-(?:(?:proj|svcacct)-)?[ \t\r\n]*[A-Za-z0-9_-]{16,}", json.dumps(messages))
        rows.append({"item_id": x["item_id"], "session_id": x["session_id"], "agent": x["agent"],
                     "behavior": x["behavior"], "target_turn_id": str(x["turn_id"]),
                     "visible_instructions": "", "messages": messages})
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    (out / "items.jsonl").write_text(text, encoding="utf-8")
    return rows, hashlib.sha256(text.encode()).hexdigest()


def write_labels(workbook, ids, out):
    import openpyxl
    wb = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
    counts = {}
    for sheet, name in (("Annotator_A", "reference_A.csv"), ("Annotator_B", "reference_B.csv")):
        labels = {}
        for row in wb[sheet].iter_rows(min_row=5, values_only=True):
            if row and row[0] in ids:
                value = row[2]
                label = "" if value is None or str(value).strip() == "" else (
                    "N/A" if str(value).strip() == "N/A" else str(int(float(value))))
                assert row[0] not in labels and label in {"", "0", "1", "2", "N/A"}
                labels[row[0]] = (row[1], label)
        assert set(labels) == ids, f"{sheet}: missing items"
        with (out / name).open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f); writer.writerow(["item_id", "behavior", "label"])
            for key in sorted(labels):
                writer.writerow([key, *labels[key]])
        counts[sheet] = sum(v[1] != "" for v in labels.values())
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows, sha = convert(args.research, args.output)
    counts = write_labels(args.workbook, {r["item_id"] for r in rows}, args.output)
    print(json.dumps({"items": len(rows), "items_sha256": sha, "labeled": counts}, indent=2))


if __name__ == "__main__":
    main()
