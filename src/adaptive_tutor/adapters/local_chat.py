"""Local vLLM bridge for the learner, coach and evaluator roles.

    python -m adaptive_tutor.adapters.local_chat --schema {utterance,decision,annotation} [flags]

local_vllm.py is the frozen RQ1 assessor adapter (its hash is pinned in the RQ1
preregistrations) and only builds the annotation payload's output schema. This
module serves the other roles from the same kind of loopback OpenAI-compatible
vLLM server and reuses local_vllm's loopback rule, annotation schema, envelope
and trace helpers unchanged. Only the decoding constraint differs by role:

- utterance: learner turns, {"content": text}
- decision:  coach choice, "none" or one (exercise_id, target_behavior) pair
             that exists in the payload's exercise bank
- annotation: evaluator scores, the same per-behavior schema as the assessor

The constraint only fixes the JSON shape; the runner's validators still decide
whether an output is accepted. TUTOR_<ROLE>_LOCAL_URL names the endpoint and
TUTOR_<ROLE>_TRACE_LOG optionally collects reasoning text and adapter errors.
Sampling flags live in the config's command list so they are frozen with the run.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from ..storage import canonical
from .local_vllm import LOOPBACK, annotation_schema, envelope, trace

RATIONALE = {"type": "string", "minLength": 1, "maxLength": 1000}


def utterance_schema(payload: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["content"],
            "properties": {"content": {"type": "string", "minLength": 1, "maxLength": 4000}}}


def decision_schema(payload: dict) -> dict:
    """One branch for "none" and one per bank exercise, matching schema.parse_decision.

    The rationale comes first so a non-reasoning model states its evidence before it
    commits to an action (coach_v2 asks for the same order).
    """
    def branch(action, exercise_id, target):
        properties = {"brief_rationale": RATIONALE, "action": {"const": action}, "exercise_id": exercise_id,
                      "target_behavior": target}
        return {"type": "object", "additionalProperties": False,
                "required": list(properties), "properties": properties}

    branches = [branch("none", {"type": "null"}, {"type": "null"})]
    branches += [branch("exercise", {"const": x["exercise_id"]}, {"const": x["behavior_id"]})
                 for x in payload["exercise_bank"]]
    return {"anyOf": branches}


SCHEMAS = {"utterance": utterance_schema, "decision": decision_schema, "annotation": annotation_schema}


def build_body(request: dict, args) -> dict:
    body = {"model": request["model"]["model_id"],
            "messages": [{"role": "system", "content": request["system_prompt"]},
                         {"role": "user", "content": canonical(request["payload"])}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": args.schema, "strict": True, "schema": SCHEMAS[args.schema](request["payload"])}},
            "max_completion_tokens": request["limits"]["max_output_tokens"],
            "temperature": request["model"]["temperature"], "top_p": args.top_p, "top_k": args.top_k,
            "min_p": args.min_p, "presence_penalty": args.presence_penalty,
            "repetition_penalty": args.repetition_penalty}
    # "default" leaves the chat template's own default (models without the kwarg).
    if args.thinking != "default":
        body["chat_template_kwargs"] = {"enable_thinking": args.thinking == "on"}
    if args.reasoning_effort:
        body["reasoning_effort"] = args.reasoning_effort
    if request["model"]["supports_seed"]:
        body["seed"] = request["sample_seed"]
    return body


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", choices=tuple(SCHEMAS), required=True)
    parser.add_argument("--thinking", choices=("on", "off", "default"), required=True)
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"))
    parser.add_argument("--top-p", type=float, required=True)
    parser.add_argument("--top-k", type=int, required=True, help="0 disables top-k")
    parser.add_argument("--min-p", type=float, required=True)
    parser.add_argument("--presence-penalty", type=float, required=True)
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument("--http-timeout", type=int, required=True,
                        help="Seconds; keep below the config's timeout_seconds")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    prefix = "TUTOR_UNKNOWN"
    try:
        request = json.load(sys.stdin.buffer)
        prefix = "TUTOR_" + request["role"].upper()
        endpoint = os.environ[prefix + "_LOCAL_URL"]
        parsed = urllib.parse.urlsplit(endpoint)
        if parsed.scheme != "http" or parsed.hostname not in LOOPBACK or parsed.username or parsed.query or parsed.fragment:
            raise ValueError("Use a plain http loopback endpoint; remote servers need the HTTPS bridge")
        body = build_body(request, args)
        http_request = urllib.request.Request(endpoint, data=canonical(body).encode("utf-8"),
                                               headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(http_request, timeout=args.http_timeout) as response:
            result = json.load(response)
        if result["choices"][0]["finish_reason"] == "abort":
            raise ConnectionError("request aborted by server")
        out, reasoning = envelope(result)
        trace(prefix, {"kind": "reasoning", "session_id": request["session_id"],
                       "provider_request_id": out["provider_request_id"], "finish_reason": result["choices"][0]["finish_reason"],
                       "usage": out["usage"], "reasoning": reasoning})
        json.dump(out, sys.stdout)
        return 0
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:2000]
        print(f"HTTP status {exc.code}: {detail}", file=sys.stderr)
        trace(prefix, {"kind": "error", "status": exc.code, "detail": detail})
        return 75 if exc.code in {408, 429, 500, 502, 503, 504} else 1
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        print("Local server transport failed", file=sys.stderr)
        trace(prefix, {"kind": "error", "status": "transport", "detail": type(exc).__name__})
        return 75
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        print("Invalid local bridge configuration or server response", file=sys.stderr)
        trace(prefix, {"kind": "error", "status": "invalid", "detail": f"{type(exc).__name__}: {exc}"[:500]})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
