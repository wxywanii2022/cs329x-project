"""tutor-assess: validate, run, audit/export and compare; no implicit live model."""
import argparse
import json
from pathlib import Path
from ..storage import write_json
from ..schema import ValidationError
from .pipeline import load_items, split_check, load_config, run, export_run
from .metrics import evaluate, compare_humans


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "run"):
        p = sub.add_parser(name)
        p.add_argument("--items", required=True, type=Path)
        p.add_argument("--config", required=name == "run", type=Path)
        p.add_argument("--split", choices=("development", "test"), default="development")
        p.add_argument("--development-items", type=Path)
        if name == "run":
            p.add_argument("--output", required=True, type=Path)
    p = sub.add_parser("audit"); p.add_argument("--run", required=True, type=Path)
    p = sub.add_parser("evaluate")
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--reference", required=True, type=Path)
    p.add_argument("--reference-provenance", choices=("unspecified", "independent-human", "model-assisted", "adjudicated", "synthetic-fixture"), default="unspecified")
    p.add_argument("--revalidate-failures", action="store_true",
                   help="Re-check recorded responses of failed calls with the current validator; no model calls")
    p.add_argument("--save", required=True, type=Path)
    p = sub.add_parser("compare-human")
    p.add_argument("--left", required=True, type=Path); p.add_argument("--right", required=True, type=Path)
    p.add_argument("--save", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            rubric = load_config(args.config)[3] if args.config else "v0.2"
            items = load_items(args.items, rubric)
            development = load_items(args.development_items, rubric) if args.development_items else None
            result = {"items": len(items), "input_valid": True, **split_check(items, args.split, development)}
        elif args.command == "run":
            result = run(args.items, args.config, args.output, args.split, args.development_items)
        elif args.command == "audit":
            result = export_run(args.run)
        elif args.command == "evaluate":
            result = evaluate(args.run, args.reference, args.reference_provenance, args.revalidate_failures); write_json(args.save, result)
        else:
            result = compare_humans(args.left, args.right); write_json(args.save, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("failed", 0) or result.get("pending", 0) else 0
    except (ValidationError, ValueError, OSError, KeyError, TypeError) as exc:
        # Configuration/data errors are not annotations. Do not expose arbitrary
        # provider stderr or any environment contents.
        parser.exit(2, f"Assessment pipeline error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
