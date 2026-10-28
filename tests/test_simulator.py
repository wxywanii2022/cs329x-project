from __future__ import annotations

import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from adaptive_tutor.adapters.base import Gateway, RecordedFailure
from adaptive_tutor.adapters.command import CommandAdapter, TransportError
from adaptive_tutor.adapters.http_bridge import build_body
from adaptive_tutor.adapters.mock import MockAdapter, mock_scores
from adaptive_tutor.analysis import agreement
from adaptive_tutor.assessment import assessment_payload
from adaptive_tutor.audit import audit_run, replay
from adaptive_tutor.coaching import coach_payload, load_exercises
from adaptive_tutor.evaluation import blind_record, percentage, validate_record_scores
from adaptive_tutor.learner import learner_payload
from adaptive_tutor.profiles import load_profiles
from adaptive_tutor.runner import ExperimentRunner, build_bundle
from adaptive_tutor.schema import BEHAVIORS, CONDITIONS, Budget, ExperimentConfig, ModelSpec, ValidationError, parse_decision, parse_scores, parse_utterance
from adaptive_tutor.storage import Journal, canonical, digest, fork_snapshot, freeze_snapshot, read_json, write_json
from adaptive_tutor.tasks import ScriptedTaskAgent, load_tasks

ROOT = Path(__file__).resolve().parents[1]


def config(**updates):
    value = read_json(ROOT / "configs" / "demo.json")
    value.update(updates)
    return ExperimentConfig.parse(value)


class ContractsTest(unittest.TestCase):
    def test_snapshot_forks_have_independent_nested_state(self):
        root = freeze_snapshot({"messages": [{"content": "before"}], "memory": {"a": []}})
        a, b = fork_snapshot(root), fork_snapshot(root)
        a["messages"][0]["content"] = "changed"
        a["memory"]["a"].append("x")
        self.assertEqual(b["messages"][0]["content"], "before")
        self.assertEqual(fork_snapshot(root)["memory"]["a"], [])
        root["memory"]["a"].append("tampering")
        with self.assertRaises(ValidationError):
            fork_snapshot(root)

    def test_configuration_rejects_bad_types_and_unknown_fields(self):
        for changes in ({"seed": True}, {"replicates": 0}, {"orientations": ["AB", "AB"]}, {"oops": 1}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                config(**changes)

    def test_family_separation_and_research_require_real_roles(self):
        with self.assertRaises(ValidationError):
            config(require_distinct_families=True)
        with self.assertRaises(ValidationError):
            config(mode="research")

    def test_development_tasks_cannot_silently_become_test_tasks(self):
        with self.assertRaises(ValidationError):
            build_bundle(config(split="test"))

    def test_profiles_are_knowledge_definitions_not_reporting_labels(self):
        profiles = load_profiles()
        self.assertEqual(len(profiles), 6)
        for profile in profiles.values():
            self.assertNotIn("reporting_group", profile.background())
            self.assertNotIn("profile_id", profile.background())

    def test_task_answer_keys_match_sources_and_accurate_controls(self):
        tasks = load_tasks()
        self.assertEqual(tasks["briefs_01", "A"]["private_answer_key"]["growth_percent"], 28)
        self.assertEqual(tasks["briefs_01", "B"]["private_answer_key"]["growth_percent"], 25)
        self.assertEqual(tasks["accurate_01", "A"]["opportunities"]["B4"], "no_opportunity")

    def test_task_agent_only_checks_targeted_requests(self):
        agent = ScriptedTaskAgent(load_tasks()["briefs_01", "A"])
        agent.opening("Three bullets please")
        agent.follow_up("Please double-check everything")
        self.assertFalse(agent.discovered)
        response = agent.follow_up("Verify the 35% growth calculation")
        self.assertIn("28%", response)
        self.assertTrue(agent.discovered)
        self.assertIn("35%", agent.finish("Thanks"))
        self.assertIn("28%", agent.finish("Correct the growth claim to 28%"))

    def test_decisions_allow_none_and_only_bank_exercises(self):
        bank = load_exercises()
        parse_decision(dict(action="none", exercise_id=None, target_behavior=None, brief_rationale="Enough practice"), bank)
        with self.assertRaises(ValidationError):
            parse_decision(dict(action="exercise", exercise_id="invented", target_behavior="B1", brief_rationale="x"), bank)

    def test_na_does_not_become_zero(self):
        self.assertIsNone(percentage([{"label": None}]))
        self.assertEqual(percentage([{"label": 2}, {"label": None}, {"label": 0}]), 50)

    def test_agreement_keeps_na_and_handles_degenerate_kappa(self):
        result = agreement(["0", "1", "2", "N/A"], ["0", "1", "0", "N/A"])
        self.assertEqual(result["raw_agreement"], 0.75)
        self.assertAlmostEqual(result["cohen_kappa"], 2 / 3)
        self.assertEqual(result["false_missed_count"], 1)
        self.assertIsNone(agreement(["2"], ["2"])["cohen_kappa"])

    def test_bridge_request_only_contains_visible_payload(self):
        body = build_body({"model": {"model_id": "exact-id", "temperature": 0.5, "supports_seed": False},
                           "limits": {"max_output_tokens": 100}, "system_prompt": "Output JSON", "payload": {"content": "hello"},
                           "sample_seed": 5, "session_id": "private-id"})
        self.assertNotIn("private-id", canonical(body))
        self.assertEqual(body["max_completion_tokens"], 100)
        self.assertNotIn("seed", body)


class RunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="tutor-tests-")
        cls.output = Path(cls.temp.name) / "run"
        cls.manifest = ExperimentRunner(config(), cls.output).run()
        cls.block = cls.manifest["blocks"][0]
        cls.folder = cls.output / "blocks" / cls.block["block_id"]
        cls.pre = read_json(cls.folder / "pre.json")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_complete_four_branch_milestone(self):
        self.assertEqual(self.manifest["task_records"], 5)
        self.assertEqual(self.manifest["failed_branches"], 0)
        self.assertEqual(self.manifest["failed_scores"], 0)
        self.assertEqual(len({b["snapshot_hash"] for b in self.block["branches"].values()}), 1)
        self.assertEqual(audit_run(self.output)["status"], "passed")

    def test_input_masks_and_private_key_exclusion(self):
        pre, state = self.pre["record"], self.pre["snapshot"]
        assessment = read_json(self.folder / "assessment.json")
        for condition in CONDITIONS[:-1]:
            payload = coach_payload(condition, pre, assessment, state["background"], load_exercises())
            self.assertEqual("background" in payload, condition != "without_background")
            self.assertEqual("assessment" in payload, condition != "without_assessment")
            for key in ("private_answer_key", "answer_key", "reporting_group", "model_config", "condition"):
                self.assertNotIn('"' + key + '"', canonical(payload))
        self.assertNotIn("background", assessment_payload(pre))
        learner = learner_payload(state, pre["task"], "review")
        self.assertIn("initial_background", learner)
        self.assertNotIn("snapshot_hash", canonical(learner))

    def test_blind_packets_hide_treatment_and_keep_local_message_ids(self):
        packet = blind_record(self.pre["record"], "opaque")
        self.assertEqual(set(packet), {"task", "messages", "opportunities", "answer_key", "final_artifact", "rubric_version", "blind_record_id"})
        self.assertEqual(packet["messages"][0]["message_id"], "m001")
        self.assertEqual(packet["messages"][0]["actor"], "evidence")
        self.assertEqual(packet["messages"][1]["actor"], "user")

    def test_post_history_retains_observed_assignment_and_source_table(self):
        state = self.pre["snapshot"]
        self.assertIn("Task assignment:", state["messages"][0]["content"])
        self.assertIn("service_table_v1", state["messages"][0]["content"])
        self.assertEqual(state["environment_state"]["task"], load_tasks()["briefs_01", "A"])
        for condition in CONDITIONS:
            branch = read_json(self.folder / "branches" / condition / "result.json")
            history = learner_payload(branch["final_state"], branch["record"]["task"], "review")["observed_history"]
            self.assertEqual(history[0]["content"], state["messages"][0]["content"])
            self.assertNotIn("private_answer_key", canonical(history))

    def test_scoring_rejects_invented_evidence_and_future_turns(self):
        record = self.pre["record"]
        value = mock_scores(record)
        value["items"][0]["supporting_spans"] = ["This span does not exist."]
        with self.assertRaises(ValidationError):
            validate_record_scores(value, record)
        value = mock_scores(record)
        value["items"][2]["evidence_message_ids"] = [record["messages"][-1]["message_id"]]
        value["items"][2]["supporting_spans"] = [record["messages"][-1]["content"][:100]]
        with self.assertRaises(ValidationError):
            validate_record_scores(value, record)

    def test_scoring_rejects_boolean_labels_and_wrong_na(self):
        for label in (True, 3, "2", None):
            value = mock_scores(self.pre["record"])
            value["items"][0]["label"] = label
            with self.subTest(label=label), self.assertRaises(ValidationError):
                parse_scores(value, self.pre["record"]["messages"])

    def test_standard_disclosure_precedes_correction_for_every_branch(self):
        for condition in CONDITIONS:
            branch = read_json(self.folder / "branches" / condition / "result.json")
            record = branch["record"]
            opportunity = record["opportunities"]["actual"]["B4"]
            self.assertLess(opportunity["disclosure_message_id"], opportunity["decision_message_id"])
            self.assertEqual(opportunity["status"], "available")
            self.assertEqual(record["task_hash"], digest(load_tasks()["briefs_01", "B"]))

    def test_control_never_receives_coach_and_post_task_has_no_coach_turns(self):
        events = Journal.read(self.output / "events.jsonl")
        for event in events:
            if event["kind"] == "call_attempt" and event["branch_id"] == "no_coaching":
                self.assertNotEqual(event["actor"], "coach")
            if event["phase"] == "post":
                self.assertNotEqual(event["actor"], "coach")

    def test_analysis_reuses_one_pre_and_preserves_paired_effect(self):
        with (self.output / "analysis" / "results.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({r["pre_record_id"] for r in rows}), 1)
        control = next(r for r in rows if r["condition"] == "no_coaching")
        for row in rows:
            self.assertAlmostEqual(float(row["paired_effect_pp"]), float(row["post_percent"]) - float(control["post_percent"]))

    def test_resume_and_replay_make_no_model_calls(self):
        before = (self.output / "events.jsonl").read_bytes()
        with patch.object(MockAdapter, "generate", side_effect=AssertionError("Unexpected model call")):
            ExperimentRunner(config(), self.output).run()
            self.assertTrue(replay(self.output))
        self.assertEqual(before, (self.output / "events.jsonl").read_bytes())

    def test_partial_run_resumes_logged_pre_calls(self):
        output = Path(self.temp.name) / "interrupted"
        original = MockAdapter.generate
        count = 0
        def interrupt(adapter, request, model):
            nonlocal count
            count += 1
            if count == 2:
                raise KeyboardInterrupt()
            return original(adapter, request, model)
        with patch.object(MockAdapter, "generate", new=interrupt), self.assertRaises(KeyboardInterrupt):
            ExperimentRunner(config(), output).run()
        resumed = ExperimentRunner(config(), output).run()
        self.assertEqual(resumed["task_records"], 5)
        self.assertEqual(audit_run(output)["status"], "passed")
        events = Journal.read(output / "events.jsonl")
        first = next(e["call_id"] for e in events if e["kind"] == "call_result")
        self.assertEqual(sum(e["kind"] == "call_result" and e["call_id"] == first for e in events if "call_id" in e), 1)

    def test_changed_inputs_cannot_resume_an_existing_run(self):
        with self.assertRaises(ValidationError):
            ExperimentRunner(config(seed=99), self.output).run()

    def test_calibration_na_and_counterbalance(self):
        output = Path(self.temp.name) / "calibration"
        result = ExperimentRunner(config(pairs=["accurate_01", "no_trigger_01", "incomplete_01"], orientations=["AB", "BA"]), output).run()
        self.assertEqual(result["task_records"], 30)
        self.assertEqual(result["failed_branches"], 0)
        for block in result["blocks"]:
            score = read_json(output / "scores" / f"{block['pre_packet']}.json")
            labels = {i["behavior_id"]: i for i in score["items"]}
            if block["pair_id"] == "accurate_01":
                self.assertIsNone(labels["B4"]["label"])
                self.assertEqual(labels["B4"]["na_reason"], "no_opportunity")
            else:
                self.assertIsNone(percentage(score["items"]))
                expected = "insufficient_evidence" if block["pair_id"] == "incomplete_01" else "no_opportunity"
                self.assertTrue(all(i["na_reason"] == expected for i in score["items"]))

    def test_budget_failure_is_retained_and_not_counted_as_a_missed_skill(self):
        output = Path(self.temp.name) / "budget"
        budget = read_json(ROOT / "configs" / "demo.json")["budget"]
        budget["max_coaching_tokens"] = 1
        result = ExperimentRunner(config(budget=budget), output).run()
        self.assertEqual(result["failed_branches"], 3)
        self.assertEqual(result["task_records"], 2)
        self.assertEqual(result["blocks"][0]["branches"]["no_coaching"]["status"], "complete")
        before = (output / "events.jsonl").read_bytes()
        ExperimentRunner(config(budget=budget), output).run()
        self.assertEqual(before, (output / "events.jsonl").read_bytes())


class GatewayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tutor-gateway-")
        self.journal = Journal(Path(self.temp.name) / "events.jsonl", "test")
        self.gateway = Gateway(config().models, Budget(), self.journal, 1)
        self.context = dict(call_id="call", session_id="opaque", block_id="block", branch_id="full", phase="pre")
        self.payload = {"stage": "request", "task": {"sources": []}}

    def tearDown(self):
        self.temp.cleanup()

    def test_transport_retries_are_fixed_and_logged(self):
        original = MockAdapter.generate
        attempts = 0
        def flaky(adapter, request, model):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise TransportError("temporary")
            return original(adapter, request, model)
        with patch.object(MockAdapter, "generate", new=flaky), patch("adaptive_tutor.adapters.base.time.sleep"):
            self.gateway.call("learner", self.payload, parse_utterance, **self.context)
        self.assertEqual(attempts, 2)
        self.assertEqual(sum(e["kind"] == "transport_failure" for e in self.journal.events), 1)

    def test_invalid_output_is_terminal_and_not_regenerated(self):
        original = MockAdapter.generate
        def invalid(adapter, request, model):
            response = original(adapter, request, model)
            response["output"] = {"unexpected": "bad"}
            return response
        with patch.object(MockAdapter, "generate", new=invalid):
            with self.assertRaises(ValidationError):
                self.gateway.call("learner", self.payload, parse_utterance, **self.context)
            with self.assertRaises(RecordedFailure):
                self.gateway.call("learner", self.payload, parse_utterance, **self.context)
        self.assertEqual(sum(e["kind"] == "call_attempt" for e in self.journal.events), 1)

    def test_command_adapter_round_trip(self):
        spec = ModelSpec(adapter="command", model_id="offline", family="mock",
                         command=(sys.executable, str(ROOT / "examples" / "mock_command_adapter.py")))
        response = CommandAdapter().generate({"role": "learner", "payload": self.payload, "sample_seed": 4,
                                               "model": {"model_id": "offline"}}, spec)
        self.assertEqual(response["model_id"], "offline")
        self.assertIn("content", response["output"])

    def test_hash_chain_detects_changed_event(self):
        self.journal.append("test", visible_content="original")
        text = self.journal.path.read_text(encoding="utf-8").replace("original", "tampered")
        self.journal.path.write_text(text, encoding="utf-8")
        with self.assertRaises(ValidationError):
            Journal.read(self.journal.path)


if __name__ == "__main__":
    unittest.main()
