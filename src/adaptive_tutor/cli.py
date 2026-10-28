"""Small CLI for running, validating, auditing and exporting experiments."""

import argparse
import json
import sys
from pathlib import Path

from .analysis import compare_annotations, export_analysis
from .audit import audit_run, replay
from .runner import ExperimentRunner, build_bundle
from .schema import ExperimentConfig
from .storage import read_json, write_json


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="tutor-sim", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Start or resume a frozen experiment")
    run.add_argument("--config", type=Path, default=Path("configs/demo.json"))
    run.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate", help="Validate configuration and bundled inputs without model calls")
    validate.add_argument("--config", type=Path, default=Path("configs/demo.json"))
    for name in ("audit", "replay", "export"):
        command = commands.add_parser(name)
        command.add_argument("--output", type=Path, required=True)
    compare = commands.add_parser("agreement", help="Compare two independently filled annotation CSVs")
    compare.add_argument("--reference", type=Path, required=True)
    compare.add_argument("--candidate", type=Path, required=True)
    compare.add_argument("--save", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            config = ExperimentConfig.parse(read_json(args.config))
            manifest = ExperimentRunner(config, args.output).run()
            result = {"output": str(args.output.resolve()), "blocks": len(manifest["blocks"]),
                      "task_records": manifest["task_records"], "failed_branches": manifest["failed_branches"],
                      "failed_scores": manifest["failed_scores"], "mode": manifest["mode"]}
            code = 1 if manifest["failed_branches"] or manifest["failed_scores"] else 0
        elif args.command == "validate":
            bundle = build_bundle(ExperimentConfig.parse(read_json(args.config)))
            result = {"status": "valid", "profiles": len(bundle["profiles"]), "task_forms": len(bundle["tasks"])}
            code = 0
        elif args.command == "audit":
            result, code = audit_run(args.output), 0
        elif args.command == "replay":
            result, code = replay(args.output), 0
        elif args.command == "export":
            result, code = export_analysis(args.output), 0
        else:
            result, code = compare_annotations(args.reference, args.candidate), 0
            if args.save:
                write_json(args.save, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (ValueError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
