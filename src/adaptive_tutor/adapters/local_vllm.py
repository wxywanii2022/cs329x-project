"""Local vLLM bridge: python -m adaptive_tutor.adapters.local_vllm [sampling flags].

For an OpenAI-compatible server on this machine (vllm serve --host 127.0.0.1).
TUTOR_<ROLE>_LOCAL_URL names the full http://127.0.0.1:<port>/v1/chat/completions
endpoint; there is no API key and loopback hosts only. Sampling flags live in the
config's command list so they are frozen with the run. Thinking output is kept
out of the envelope; set TUTOR_<ROLE>_TRACE_LOG to append it (and adapter errors)
to a private JSONL file for later error analysis.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from ..storage import canonical

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
STATUSES = ("no_opportunity", "insufficient_evidence")


def annotation_schema(payload: dict) -> dict:
    """Decoding constraint for the final answer; core.validate_annotation still decides.

    One branch per consistent label/status/na_reason combination, so the grammar
    cannot emit e.g. a numeric label with an N/A reason. Exact-quote checks remain
    with the validator.
    """
    ids = [m["turn_id"] for m in payload["messages"]]
    evidence = {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["turn_id", "quote"],
        "properties": {"turn_id": {"enum": ids}, "quote": {"type": "string", "minLength": 1, "maxLength": 500}}}}
    if not ids:
        evidence = {"type": "array", "maxItems": 0}

    def branch(label, status, na_reason, evidence):
        properties = {"behavior": {"const": payload["behavior"]}, "label": label,
                      "opportunity_status": {"const": status}, "na_reason": na_reason,
                      "reason": {"type": "string", "minLength": 1, "maxLength": 1000},
                      "confidence": {"enum": ["high", "medium", "low"]},
                      "unclear_rule": {"type": "string", "maxLength": 2000}, "evidence": evidence}
        return {"type": "object", "additionalProperties": False,
                "required": list(properties), "properties": properties}

    branches = [branch({"type": "null"}, s, {"const": s}, evidence) for s in STATUSES]
    if payload["target_turn_id"] is None:
        branches = branches[1:]
    else:
        branches.insert(0, branch({"enum": [0, 1, 2]}, "available", {"type": "null"}, {**evidence, "minItems": 1}))
    return {"anyOf": branches}


def build_body(request: dict, args) -> dict:
    # Same message construction as http_bridge: versioned system prompt plus the
    # masked payload as canonical JSON.
    body = {"model": request["model"]["model_id"],
            "messages": [{"role": "system", "content": request["system_prompt"]},
                         {"role": "user", "content": canonical(request["payload"])}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "annotation", "strict": True, "schema": annotation_schema(request["payload"])}},
            "max_completion_tokens": request["limits"]["max_output_tokens"],
            "temperature": request["model"]["temperature"], "top_p": args.top_p, "top_k": args.top_k,
            "min_p": args.min_p, "presence_penalty": args.presence_penalty,
            "repetition_penalty": args.repetition_penalty,
            "chat_template_kwargs": {"enable_thinking": args.thinking == "on"}}
    if request["model"]["supports_seed"]:
        body["seed"] = request["sample_seed"]
    return body


def envelope(result: dict) -> tuple[dict, str | None]:
    choice = result["choices"][0]
    message = choice["message"]
    try:
        output = json.loads(message["content"]) if choice["finish_reason"] == "stop" else {"invalid_completion": choice["finish_reason"]}
    except (ValueError, TypeError):
        output = {"invalid_json": message.get("content")}
    # Preserve malformed outputs for the runner's terminal validation failure;
    # never repair or resample substantive model behavior.
    return ({"output": output,
             "usage": {"input_tokens": result["usage"]["prompt_tokens"],
                       "output_tokens": result["usage"]["completion_tokens"], "estimated": False},
             "provider_request_id": result["id"], "model_id": result["model"],
             "tool_calls": message.get("tool_calls") or []},
            message.get("reasoning") or message.get("reasoning_content"))


def trace(prefix: str, record: dict) -> None:
    path = os.environ.get(prefix + "_TRACE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(canonical(record) + "\n")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thinking", choices=("on", "off"), required=True)
    parser.add_argument("--top-p", type=float, required=True)
    parser.add_argument("--top-k", type=int, required=True)
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
            # The server cancelled the request (e.g. shutdown); not a model outcome.
            raise ConnectionError("request aborted by server")
        out, reasoning = envelope(result)
        trace(prefix, {"kind": "reasoning", "session_id": request["session_id"],
                       "provider_request_id": out["provider_request_id"], "finish_reason": result["choices"][0]["finish_reason"],
                       "usage": out["usage"], "reasoning": reasoning})
        json.dump(out, sys.stdout)
        return 0
    except urllib.error.HTTPError as exc:
        # vLLM error bodies describe the request (e.g. context length), not secrets.
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
