"""No network, credentials or private annotations used by these regressions."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from adaptive_tutor.rq1.core import prepare_payload, validate_annotation, rubric_prompt
from adaptive_tutor.rq1.pipeline import run, load_config, load_items, split_check, audit_run
from adaptive_tutor.rq1.metrics import evaluate, compare_humans
from adaptive_tutor.rq1.mock import mock_annotation
from adaptive_tutor.adapters.mock import MockAdapter
from adaptive_tutor.schema import ValidationError, Budget, ModelSpec
from adaptive_tutor.storage import read_json, write_json, canonical, Journal
from adaptive_tutor.assessment import assessment_payload, assess
from adaptive_tutor.adapters.base import Gateway

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "examples/assessment_items.synthetic.jsonl"
CONFIG = ROOT / "configs/assessment.mock.json"


def item():
    return {"behavior": "B3", "target_turn_id": "u2", "messages": [
        {"turn_id": "a1", "role": "assistant", "content": "There was 35% growth."},
        {"turn_id": "u2", "role": "user", "content": "Verify the 35% growth calculation."},
        {"turn_id": "a3", "role": "assistant", "content": "FUTURE_ONLY_SENTINEL"}],
        "background": "PROFILE_SENTINEL", "label": "HUMAN_LABEL_SENTINEL",
        "opportunity_status": "ORACLE_SENTINEL", "answer_key": "ANSWER_SENTINEL"}


class PrefixTests(unittest.TestCase):
    def test_allowlist_excludes_metadata_oracle_and_future(self):
        payload = prepare_payload(item())
        self.assertEqual(len(payload["messages"]), 2)
        for secret in ("FUTURE_ONLY", "PROFILE_", "HUMAN_LABEL_", "ORACLE_", "ANSWER_"):
            self.assertNotIn(secret, canonical(payload))

    def test_changing_or_malforming_future_does_not_change_payload(self):
        original = item(); changed = copy.deepcopy(original)
        changed["messages"][2:] = [{"invalid": ["unseen"]}]
        self.assertEqual(prepare_payload(original), prepare_payload(changed))

    def test_source_order_not_lexical_turn_order(self):
        x = item(); x["messages"][0]["turn_id"] = "turn-99"; x["messages"][1]["turn_id"] = "turn-1"; x["target_turn_id"] = "turn-1"
        self.assertEqual([m["turn_id"] for m in prepare_payload(x)["messages"]], ["turn-99", "turn-1"])

    def test_commands_empty_and_ineligible_targets(self):
        x = item(); x["messages"].insert(0, {"turn_id": "cmd", "role": "user", "content": " /help"})
        x["messages"].insert(0, {"turn_id": "empty", "role": "user", "content": " "})
        self.assertEqual(len(prepare_payload(x)["messages"]), 2)
        for target in ("missing", "cmd", "empty", "a1"):
            x["target_turn_id"] = target
            with self.subTest(target=target), self.assertRaises(ValidationError):
                prepare_payload(x)

    def test_duplicate_ids_and_missing_record(self):
        x = item(); x["messages"][0]["turn_id"] = "u2"
        with self.assertRaises(ValidationError): prepare_payload(x)
        payload = prepare_payload({"behavior": "B4", "messages": [], "target_turn_id": None})
        self.assertEqual(validate_annotation(mock_annotation(payload), payload)["na_reason"], "insufficient_evidence")
        with self.assertRaises(ValidationError):
            prepare_payload({"behavior": "B4", "messages": [], "target_turn_id": "missing"})

    def test_output_rejects_future_quotes_and_bad_labels(self):
        payload = prepare_payload(item())
        for label in (True, "2", 3):
            output = mock_annotation(payload); output["label"] = label
            with self.subTest(label=label), self.assertRaises(ValidationError): validate_annotation(output, payload)
        output = mock_annotation(payload); output["evidence"] = [{"turn_id": "a3", "quote": "FUTURE_ONLY_SENTINEL"}]
        with self.assertRaises(ValidationError): validate_annotation(output, payload)
        output = mock_annotation(payload); output["evidence"][0]["quote"] = "fabricated quote"
        with self.assertRaises(ValidationError): validate_annotation(output, payload)

    def test_valid_na_prediction_not_overridden_by_hidden_opportunity(self):
        payload = prepare_payload(item()); output = mock_annotation(payload)
        output.update(label=None, opportunity_status="insufficient_evidence", na_reason="insufficient_evidence")
        self.assertIsNone(validate_annotation(output, payload)["label"])
        output["na_reason"] = "no_opportunity"
        with self.assertRaises(ValidationError): validate_annotation(output, payload)

    def test_frozen_and_simulation_rubrics_are_explicitly_distinct(self):
        self.assertIn("Specification and Verification Behaviors — v0.2", rubric_prompt("v0.2"))
        self.assertIn("candidate", rubric_prompt("sim-opportunities-v1"))
        with self.assertRaises(ValidationError): rubric_prompt("v0.3")

    def test_config_has_no_default_team_model(self):
        with self.assertRaisesRegex(ValidationError, "not configured"):
            load_config(ROOT / "configs/assessment.team.example.json")

    def test_participant_disjoint_guard(self):
        rows = load_items(ITEMS)
        with self.assertRaises(ValidationError): split_check(rows, "test")
        with self.assertRaises(ValidationError): split_check(rows, "test", rows)
        dev = copy.deepcopy(rows)
        for r in dev:
            for key in ("item_id", "session_id", "participant_id"): r[key] = "dev-" + r[key]
        self.assertTrue(split_check(rows, "test", dev)["participant_disjoint_checked"])
        rows[0]["participant_id"] = None
        with self.assertRaises(ValidationError): split_check(rows, "test", dev)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.output = Path(self.tmp.name) / "run"
    def tearDown(self): self.tmp.cleanup()

    def test_run_resume_and_reference_comparison(self):
        result = run(ITEMS, CONFIG, self.output)
        self.assertEqual((result["completed"], result["failed"]), (4, 0))
        before = (self.output / "events.jsonl").read_bytes()
        with patch.object(MockAdapter, "generate", side_effect=AssertionError("Unexpected call")):
            run(ITEMS, CONFIG, self.output)
        self.assertEqual(before, (self.output / "events.jsonl").read_bytes())
        report = evaluate(self.output, ROOT / "examples/assessment_reference.synthetic.csv", "synthetic-fixture")
        self.assertEqual(report["overall"]["raw_agreement"], 1)
        self.assertEqual(report["overall"]["false_missed_rate"], 0)
        events = Journal.read(self.output / "events.jsonl")
        calls = [e for e in events if e["kind"] == "call_attempt"]
        self.assertEqual(len({e["request"]["session_id"] for e in calls}), 4)
        for e in calls:
            self.assertNotIn("item_id", e["request"]["payload"])
            self.assertNotIn("participant_id", e["request"]["payload"])
            self.assertNotIn("HUMAN_LABEL", canonical(e["request"]))

    def test_command_adapter_round_trip_uses_same_assessment_contract(self):
        configuration = read_json(CONFIG)
        configuration["model"].update(adapter="command", command=[sys.executable, str(ROOT / "examples/mock_command_adapter.py")])
        path = Path(self.tmp.name) / "command.json"
        write_json(path, configuration)
        result = run(ITEMS, path, self.output)
        self.assertEqual((result["completed"], result["failed"]), (4, 0))
        self.assertFalse(result["validated_assessor"])
        frozen, predictions = audit_run(self.output)
        self.assertTrue(all(p["usage"]["estimated"] for p in predictions))

    def test_failure_not_na_and_no_retry_of_substantive_output(self):
        original = MockAdapter.generate
        def invalid(adapter, request, model):
            response = original(adapter, request, model)
            response["output"]["label"] = "INVALID"
            return response
        with patch.object(MockAdapter, "generate", new=invalid):
            result = run(ITEMS, CONFIG, self.output)
        self.assertEqual((result["failed"], result["labels"]), (4, {}))
        with patch.object(MockAdapter, "generate", side_effect=AssertionError("Retry")):
            run(ITEMS, CONFIG, self.output)
        with (self.output / "labels.csv").open() as f:
            self.assertTrue(all(r["label"] == "" for r in csv.DictReader(f)))
        report = evaluate(self.output, ROOT / "examples/assessment_reference.synthetic.csv")
        self.assertEqual(report["overall"]["n"], 0)
        self.assertEqual(report["labeled_references_without_successful_prediction"], 4)

    def test_spreadsheet_exports_escape_formulas_but_keep_raw_json(self):
        original = MockAdapter.generate
        def formula(adapter, request, model):
            response = original(adapter, request, model)
            response["output"]["reason"] = "=1+1"
            return response
        with patch.object(MockAdapter, "generate", new=formula):
            run(ITEMS, CONFIG, self.output)
        with (self.output / "labels.csv").open() as f:
            self.assertTrue(all(row["reason"] == "'=1+1" for row in csv.DictReader(f)))
        _, rows = audit_run(self.output)
        self.assertTrue(all(row["annotation"]["reason"] == "=1+1" for row in rows))

    def test_changed_config_and_tampered_journal_rejected(self):
        run(ITEMS, CONFIG, self.output)
        changed = read_json(CONFIG); changed["seed"] += 1
        path = Path(self.tmp.name) / "changed.json"; write_json(path, changed)
        with self.assertRaises(ValidationError): run(ITEMS, path, self.output)
        journal = self.output / "events.jsonl"
        journal.write_text(journal.read_text().replace("three bullets", "BAD_CHANGE", 1))
        with self.assertRaises(ValidationError): audit_run(self.output)

    def test_reference_not_accepted_as_input_metadata(self):
        raw = json.loads(ITEMS.read_text().splitlines()[0]); raw["label"] = 2
        path = Path(self.tmp.name) / "leaky.jsonl"; path.write_text(json.dumps(raw) + "\n")
        with self.assertRaises(ValidationError): load_items(path)

    def test_compare_humans_preserves_blanks_and_does_not_claim_independence(self):
        a, b = Path(self.tmp.name) / "a.csv", Path(self.tmp.name) / "b.csv"
        a.write_text("item_id,label\na,2\nb,N/A\nc,\n")
        b.write_text("item_id,label\na,0\nb,N/A\nc,1\n")
        result = compare_humans(a, b)
        self.assertEqual(result["jointly_labeled"], 2)
        self.assertEqual(result["agreement"]["false_missed_rate"], .5)
        self.assertFalse(result["independence_verified"])

    def test_simulation_uses_four_fresh_prefix_calls_and_keeps_na_errors(self):
        from adaptive_tutor.runner import ExperimentRunner
        from adaptive_tutor.schema import ExperimentConfig
        config = ExperimentConfig.parse(read_json(ROOT / "configs/demo.json"))
        folder = Path(self.tmp.name) / "sim"
        manifest = ExperimentRunner(config, folder).run()
        record = read_json(folder / "blocks" / manifest["blocks"][0]["block_id"] / "pre.json")["record"]
        # Hidden oracle labels must not affect any assessor request.
        for behavior in ("B1", "B2", "B3", "B4"):
            changed = copy.deepcopy(record)
            changed["opportunities"]["actual"][behavior]["status"] = "ORACLE_SENTINEL"
            changed["opportunities"]["prescribed"][behavior] = "ORACLE_SENTINEL"
            self.assertEqual(assessment_payload(record, behavior), assessment_payload(changed, behavior))
        events = Journal.read(folder / "events.jsonl")
        calls = [e for e in events if e["kind"] == "call_attempt" and e["request"]["role"] == "assessment"]
        self.assertEqual(len(calls), 4)
        self.assertEqual(len({e["request"]["session_id"] for e in calls}), 4)
        for e in calls:
            self.assertNotIn("opportunities", e["request"]["payload"])
        original = MockAdapter.generate
        def disagree(adapter, request, model):
            response = original(adapter, request, model)
            response["output"].update(label=None, opportunity_status="no_opportunity", na_reason="no_opportunity")
            return response
        gateway = Gateway(config.models, Budget(), Journal(Path(self.tmp.name) / "disagree.jsonl", "test"), 1)
        with patch.object(MockAdapter, "generate", new=disagree):
            result, _ = assess(gateway, record, call_id="different", session_id="different", block_id="b", branch_id=None, phase="assessment")
        self.assertTrue(all(x["label"] is None for x in result["items"]))


if __name__ == "__main__": unittest.main()
