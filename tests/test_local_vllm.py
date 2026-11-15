"""Local vLLM bridge regressions: no server, GPU or network; urlopen is patched."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from adaptive_tutor.adapters import local_vllm
from adaptive_tutor.rq1.core import prepare_payload, rubric_prompt, validate_annotation
from adaptive_tutor.rq1.mock import mock_annotation
from adaptive_tutor.rq1.pipeline import load_items
from adaptive_tutor.schema import ValidationError

try:
    import jsonschema
except ImportError:  # Optional: installed alongside vLLM, not a project dependency.
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "examples/assessment_items.synthetic.jsonl"
ARGS = ["--thinking", "on", "--top-p", "0.95", "--top-k", "20", "--min-p", "0",
        "--presence-penalty", "0", "--http-timeout", "60"]
URL = "http://127.0.0.1:8000/v1/chat/completions"


def request(payload, supports_seed=True):
    return {"protocol_version": "1", "role": "assessment", "session_id": "s1", "system_prompt": rubric_prompt("v0.2"),
            "prompt_version": "decision-point-v1/v0.2", "payload": payload, "sample_seed": 1234,
            "model": {"model_id": "repo@rev", "temperature": 1.0, "supports_seed": supports_seed},
            "limits": {"max_output_tokens": 32768, "max_total_tokens": None}}


def completion(content, finish="stop"):
    return {"id": "chatcmpl-1", "model": "repo@rev", "usage": {"prompt_tokens": 900, "completion_tokens": 120},
            "choices": [{"finish_reason": finish, "message": {"content": content, "reasoning": "THINKING_SENTINEL"}}]}


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *exc): return False


def invoke(req, reply=None, error=None, env=None):
    stdin = io.TextIOWrapper(io.BytesIO(json.dumps(req).encode("utf-8")), encoding="utf-8")
    stdout = io.StringIO()
    opened = patch("urllib.request.urlopen", side_effect=error) if error else \
        patch("urllib.request.urlopen", return_value=Response(json.dumps(reply).encode("utf-8")))
    with opened as urlopen, patch("sys.stdin", stdin), patch("sys.stdout", stdout), \
            patch.dict(os.environ, {"TUTOR_ASSESSMENT_LOCAL_URL": URL, **(env or {})}), \
            patch("sys.stderr", io.StringIO()):
        code = local_vllm.main(ARGS)
    return code, stdout.getvalue(), urlopen


class LocalVllmTests(unittest.TestCase):
    def setUp(self):
        self.payloads = [x["payload"] for x in load_items(ITEMS)]

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_schema_accepts_contract_outputs_and_rejects_inconsistent_ones(self):
        for payload in self.payloads:
            jsonschema.validate(validate_annotation(mock_annotation(payload), payload), local_vllm.annotation_schema(payload))
        payload = self.payloads[0]
        good = mock_annotation(payload)
        self.assertEqual(good["label"], 2)
        validator = jsonschema.Draft202012Validator(local_vllm.annotation_schema(payload))
        for bad in ({**good, "na_reason": "no_opportunity"}, {**good, "evidence": []},
                    {**good, "label": None, "opportunity_status": "no_opportunity", "na_reason": "insufficient_evidence"},
                    {**good, "behavior": "B4"}, {**good, "evidence": [{"turn_id": "a2", "quote": "later"}]},
                    {**good, "extra": 1}):
            with self.subTest(bad=bad):
                self.assertFalse(validator.is_valid(bad))

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_missing_record_schema_only_allows_insufficient_evidence(self):
        payload = prepare_payload({"behavior": "B1", "target_turn_id": None, "messages": [], "visible_instructions": ""})
        validator = jsonschema.Draft202012Validator(local_vllm.annotation_schema(payload))
        na = {"behavior": "B1", "label": None, "opportunity_status": "insufficient_evidence", "na_reason": "insufficient_evidence",
              "reason": "No record.", "confidence": "high", "unclear_rule": "", "evidence": []}
        self.assertTrue(validator.is_valid(na))
        self.assertFalse(validator.is_valid({**na, "opportunity_status": "no_opportunity", "na_reason": "no_opportunity"}))

    def test_body_uses_prefix_payload_sampling_flags_and_seed_only_when_supported(self):
        args = local_vllm.parse_args(ARGS)
        body = local_vllm.build_body(request(self.payloads[0]), args)
        self.assertNotIn("This later reply", json.dumps(body))
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertEqual((body["seed"], body["top_k"], body["temperature"], body["max_completion_tokens"]), (1234, 20, 1.0, 32768))
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": True})
        self.assertNotIn("seed", local_vllm.build_body(request(self.payloads[0], supports_seed=False), args))

    def test_envelope_round_trip_keeps_reasoning_out_but_traces_it(self):
        payload = self.payloads[0]
        annotation = mock_annotation(payload)
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "trace.jsonl"
            code, out, _ = invoke(request(payload), completion(json.dumps(annotation)), env={"TUTOR_ASSESSMENT_TRACE_LOG": str(log)})
            self.assertEqual(code, 0)
            envelope = json.loads(out)
            self.assertEqual(set(envelope), {"output", "usage", "provider_request_id", "model_id", "tool_calls"})
            self.assertEqual(validate_annotation(envelope["output"], payload), annotation)
            self.assertEqual(envelope["usage"], {"input_tokens": 900, "output_tokens": 120, "estimated": False})
            self.assertNotIn("THINKING_SENTINEL", out)
            self.assertEqual(json.loads(log.read_text())["reasoning"], "THINKING_SENTINEL")

    def test_truncated_completion_is_preserved_as_invalid_not_repaired(self):
        payload = self.payloads[0]
        code, out, _ = invoke(request(payload), completion('{"behavior":', finish="length"))
        self.assertEqual((code, json.loads(out)["output"]), (0, {"invalid_completion": "length"}))
        with self.assertRaises(ValidationError):
            validate_annotation(json.loads(out)["output"], payload)

    def test_only_loopback_http_and_exit_codes(self):
        req = request(self.payloads[0])
        for url in ("http://example.org/v1/chat/completions", "https://127.0.0.1:8000/v1/chat/completions"):
            with self.subTest(url=url):
                code, _, urlopen = invoke(req, completion("{}"), env={"TUTOR_ASSESSMENT_LOCAL_URL": url})
                self.assertEqual(code, 1)
                urlopen.assert_not_called()
        self.assertEqual(invoke(req, completion("", finish="abort"))[0], 75)  # server shutdown, not a model outcome
        http = lambda status: urllib.error.HTTPError(URL, status, "x", {}, io.BytesIO(b"context too long"))
        self.assertEqual(invoke(req, error=urllib.error.URLError("refused"))[0], 75)
        self.assertEqual(invoke(req, error=http(503))[0], 75)
        self.assertEqual(invoke(req, error=http(400))[0], 1)


if __name__ == "__main__": unittest.main()
