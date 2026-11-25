"""Local chat bridge (learner/coach/evaluator) regressions: no GPU, model or network.

Unit tests patch urlopen. The end-to-end test runs the RQ2 pilot configuration,
with every role behind its real process adapter, against a fake OpenAI-compatible
server on 127.0.0.1 that answers with schema-valid lexical mock outputs.
"""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from adaptive_tutor.adapters import local_chat
from adaptive_tutor.audit import audit_run
from adaptive_tutor.coaching import coach_payload, load_exercises
from adaptive_tutor.rq1.mock import mock_annotation
from adaptive_tutor.runner import ExperimentRunner
from adaptive_tutor.schema import ExperimentConfig, ValidationError, parse_decision, parse_utterance
from adaptive_tutor.storage import read_json

try:
    import jsonschema
except ImportError:  # Optional: installed alongside vLLM, not a project dependency.
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "configs/rq2-pilot/pilot.json"
URL = "http://127.0.0.1:8000/v1/chat/completions"
ARGS = ["--schema", "utterance", "--thinking", "off", "--top-p", "0.95", "--top-k", "64", "--min-p", "0",
        "--presence-penalty", "0", "--http-timeout", "60"]


def request(role, payload, supports_seed=True):
    return {"protocol_version": "1", "role": role, "session_id": "s1", "system_prompt": "prompt",
            "prompt_version": role + "_v1", "payload": payload, "sample_seed": 1234,
            "model": {"model_id": "repo@rev", "temperature": 1.0, "supports_seed": supports_seed},
            "limits": {"max_output_tokens": 1500, "max_total_tokens": None}}


def completion(content, finish="stop"):
    return {"id": "chatcmpl-1", "model": "repo@rev", "usage": {"prompt_tokens": 50, "completion_tokens": 9},
            "choices": [{"finish_reason": finish, "message": {"content": content, "reasoning": "THINKING_SENTINEL"}}]}


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *exc): return False


def invoke(args, req, reply, env):
    stdin = io.TextIOWrapper(io.BytesIO(json.dumps(req).encode("utf-8")), encoding="utf-8")
    stdout = io.StringIO()
    with patch("urllib.request.urlopen", return_value=Response(json.dumps(reply).encode("utf-8"))) as urlopen, \
            patch("sys.stdin", stdin), patch("sys.stdout", stdout), patch.dict(os.environ, env), \
            patch("sys.stderr", io.StringIO()):
        code = local_chat.main(args)
    return code, stdout.getvalue(), urlopen


def mock_output(body: dict) -> dict:
    """Schema-valid fake reply chosen by the requested schema name."""
    payload = json.loads(body["messages"][1]["content"])
    name = body["response_format"]["json_schema"]["name"]
    if name == "annotation":
        return mock_annotation(payload)
    if name == "decision":
        return {"action": "exercise", "exercise_id": "check_v1", "target_behavior": "B3",
                "brief_rationale": "The visible review did not target the growth claim."}
    replies = {"request": "Please draft a two-bullet summary for my manager and show the calculation from the source table.",
               "review": "Can you verify the growth percent? Please recalculate it.",
               "correction": "Please correct the growth claim to the figure from the table, 28%, instead.",
               "practice": "I would ask for the calculation and check the base."}
    return {"content": replies[payload["stage"]]}


class FakeServer(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.bodies.append(body)
        reply = {"id": f"fake-{len(self.server.bodies)}", "model": body["model"],
                 "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                 "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(mock_output(body))}}]}
        data = json.dumps(reply).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class LocalChatTests(unittest.TestCase):
    def setUp(self):
        self.bank = load_exercises()

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_decision_schema_admits_exactly_the_valid_bank_decisions(self):
        schema = local_chat.decision_schema({"exercise_bank": self.bank})
        validator = jsonschema.Draft202012Validator(schema)
        none = {"action": "none", "exercise_id": None, "target_behavior": None, "brief_rationale": "Not needed."}
        valid = [none] + [{"action": "exercise", "exercise_id": x["exercise_id"], "target_behavior": x["behavior_id"],
                           "brief_rationale": "Targets the gap."} for x in self.bank]
        for value in valid:
            with self.subTest(value=value):
                self.assertTrue(validator.is_valid(value))
                parse_decision(value, self.bank)
        good = valid[1]
        for bad in ({**good, "target_behavior": "B4"}, {**good, "exercise_id": "invented_v1"},
                    {**none, "exercise_id": "check_v1"}, {**good, "brief_rationale": ""}, {**good, "extra": 1}):
            with self.subTest(bad=bad):
                self.assertFalse(validator.is_valid(bad))

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_utterance_schema_matches_learner_contract(self):
        validator = jsonschema.Draft202012Validator(local_chat.utterance_schema({}))
        self.assertTrue(validator.is_valid({"content": "Please check the 35%."}))
        parse_utterance({"content": "Please check the 35%."})
        for bad in ({"content": ""}, {}, {"content": "x", "state": "improved"}):
            self.assertFalse(validator.is_valid(bad))

    def test_body_flags_thinking_effort_and_seed(self):
        args = local_chat.parse_args(ARGS)
        body = local_chat.build_body(request("learner", {"stage": "request"}), args)
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertEqual((body["seed"], body["top_k"], body["temperature"], body["max_completion_tokens"]), (1234, 64, 1.0, 1500))
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("reasoning_effort", body)
        self.assertEqual(body["response_format"]["json_schema"]["name"], "utterance")
        evaluator = local_chat.parse_args(["--schema", "annotation", "--thinking", "default", "--reasoning-effort", "high",
                                           "--top-p", "1", "--top-k", "0", "--min-p", "0", "--presence-penalty", "0",
                                           "--http-timeout", "60"])
        payload = {"behavior": "B3", "target_turn_id": "m3", "messages": [{"turn_id": "m3", "role": "user", "content": "x"}]}
        body = local_chat.build_body(request("evaluator", payload, supports_seed=False), evaluator)
        self.assertNotIn("chat_template_kwargs", body)
        self.assertNotIn("seed", body)
        self.assertEqual(body["reasoning_effort"], "high")

    def test_round_trip_uses_role_endpoint_and_keeps_reasoning_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "trace.jsonl"
            code, out, urlopen = invoke(ARGS, request("learner", {"stage": "review"}),
                                        completion(json.dumps({"content": "Check the 35% please."})),
                                        {"TUTOR_LEARNER_LOCAL_URL": URL, "TUTOR_LEARNER_TRACE_LOG": str(log)})
            self.assertEqual(code, 0)
            self.assertEqual(urlopen.call_args[0][0].full_url, URL)
            envelope = json.loads(out)
            self.assertEqual(parse_utterance(envelope["output"]), {"content": "Check the 35% please."})
            self.assertNotIn("THINKING_SENTINEL", out)
            self.assertEqual(json.loads(log.read_text())["reasoning"], "THINKING_SENTINEL")

    def test_only_loopback_and_invalid_output_is_preserved(self):
        req = request("coach", {"exercise_bank": self.bank})
        args = ["--schema", "decision", *ARGS[2:]]
        for url in ("http://example.org/v1/chat/completions", "https://127.0.0.1:8000/v1/chat/completions"):
            code, _, urlopen = invoke(args, req, completion("{}"), {"TUTOR_COACH_LOCAL_URL": url})
            self.assertEqual(code, 1)
            urlopen.assert_not_called()
        code, out, _ = invoke(args, req, completion('{"action":', finish="length"), {"TUTOR_COACH_LOCAL_URL": URL})
        self.assertEqual((code, json.loads(out)["output"]), (0, {"invalid_completion": "length"}))
        with self.assertRaises(ValidationError):
            parse_decision(json.loads(out)["output"], self.bank)

    def test_pilot_config_end_to_end_through_process_adapters(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeServer)
        server.bodies = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"
        config = read_json(PILOT)
        config.update(profiles=["novice_a"], pairs=["briefs_01"], orientations=["AB"], replicates=1)
        for spec in config["models"].values():
            spec["command"] = [sys.executable, *spec["command"][1:]]
        env = {f"TUTOR_{r}_LOCAL_URL": url for r in ("LEARNER", "ASSESSMENT", "COACH", "EVALUATOR")}
        try:
            with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {**env, "PYTHONPATH": str(ROOT / "src")}):
                manifest = ExperimentRunner(ExperimentConfig.parse(config), Path(tmp)).run()
                self.assertEqual((manifest["failed_branches"], manifest["failed_scores"], manifest["task_records"]), (0, 0, 5))
                self.assertEqual(audit_run(Path(tmp))["status"], "passed")
                coached = read_json(next(Path(tmp).glob("blocks/*/branches/full/result.json")))
                self.assertEqual(coached["decision"]["exercise_id"], "check_v1")
        finally:
            server.shutdown()
            server.server_close()
        names = {}
        for body in server.bodies:
            names.setdefault(body["model"], set()).add(body["response_format"]["json_schema"]["name"])
        ids = {role: spec["model_id"] for role, spec in config["models"].items()}
        self.assertEqual(names, {ids["learner"]: {"utterance"}, ids["coach"]: {"decision"},
                                 ids["assessment"]: {"annotation"}, ids["evaluator"]: {"annotation"}})
        by_model = {b["model"]: b for b in server.bodies}
        self.assertEqual(by_model[ids["evaluator"]]["reasoning_effort"], "high")
        self.assertEqual(by_model[ids["learner"]]["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(by_model[ids["assessment"]]["chat_template_kwargs"], {"enable_thinking": True})


if __name__ == "__main__": unittest.main()
