"""Optional Chat Completions bridge: python -m adaptive_tutor.adapters.http_bridge.

Each role uses TUTOR_<ROLE>_URL and TUTOR_<ROLE>_API_KEY. URLs must name the full
HTTPS chat/completions endpoint. No provider is contacted until explicitly run.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from ..storage import canonical


def build_body(request: dict) -> dict:
    body = {"model": request["model"]["model_id"],
            "messages": [{"role": "system", "content": request["system_prompt"]},
                         {"role": "user", "content": canonical(request["payload"])}],
            "response_format": {"type": "json_object"},
            "max_completion_tokens": request["limits"]["max_output_tokens"],
            "temperature": request["model"]["temperature"], "store": False}
    if request["model"]["supports_seed"]:
        body["seed"] = request["sample_seed"]
    return body


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward a role's API key to a different endpoint after a redirect.
        return None


def main() -> int:
    try:
        request = json.load(sys.stdin)
        prefix = "TUTOR_" + request["role"].upper()
        endpoint, key = os.environ[prefix + "_URL"], os.environ[prefix + "_API_KEY"]
        parsed = urllib.parse.urlsplit(endpoint)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Use a full HTTPS endpoint without credentials, query parameters or fragments")
        body = build_body(request)
        http_request = urllib.request.Request(endpoint, data=canonical(body).encode("utf-8"),
                                               headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                                               method="POST")
        with urllib.request.build_opener(NoRedirect).open(http_request, timeout=90) as response:
            result = json.load(response)
            request_id = response.headers.get("x-request-id") or result["id"]
        choice = result["choices"][0]
        message = choice["message"]
        try:
            output = json.loads(message["content"]) if choice["finish_reason"] == "stop" and not message.get("refusal") else {"invalid_completion": choice["finish_reason"]}
        except (ValueError, TypeError):
            output = {"invalid_json": message.get("content")}
        # Preserve malformed schema outputs and usage for the runner's terminal
        # validation failure. Never repair or resample substantive model behavior.
        envelope = {"output": output,
                    "usage": {"input_tokens": result["usage"]["prompt_tokens"],
                              "output_tokens": result["usage"]["completion_tokens"], "estimated": False},
                    "provider_request_id": request_id, "model_id": result["model"],
                    "tool_calls": message.get("tool_calls") or []}
        json.dump(envelope, sys.stdout)
        return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP status {exc.code}", file=sys.stderr)
        return 75 if exc.code in {408, 429, 500, 502, 503, 504} else 1
    except (urllib.error.URLError, TimeoutError):
        print("Provider transport failed", file=sys.stderr)
        return 75
    except (ValueError, KeyError, TypeError):
        print("Invalid bridge configuration or provider response", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
