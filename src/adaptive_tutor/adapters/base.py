"""Role calls with recorded requests, fixed retries and exact replay of accepted responses."""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from ..schema import Budget, ModelSpec, ValidationError, integer, keys, require, string
from ..storage import Journal, canonical, digest
from .command import CommandAdapter, TransportError
from .mock import MockAdapter

PROMPTS = Path(__file__).parents[1] / "prompts"


class BudgetExceeded(RuntimeError):
    pass


class RecordedFailure(RuntimeError):
    pass


class Gateway:
    def __init__(self, models: dict[str, ModelSpec], budget: Budget, journal: Journal, seed: int):
        self.models, self.budget, self.journal, self.seed = models, budget, journal, seed
        self.cache = {e["call_id"]: e for e in journal.events if e["kind"] in {"call_result", "call_failure"}}
        self.transports = {"mock": MockAdapter(), "command": CommandAdapter()}

    def call(self, role: str, payload: dict, validator, *, call_id: str, session_id: str,
             block_id: str, branch_id: str | None, phase: str,
             max_output_tokens: int | None = None, total_token_allowance: int | None = None,
             prompt_text: str | None = None, prompt_version: str | None = None) -> tuple[dict, dict]:
        model = self.models[role]
        require((prompt_text is None) == (prompt_version is None), "Custom prompt needs text and version")
        prompt_version = prompt_version or role + "_v1"
        request = {"protocol_version": "1", "role": role, "session_id": session_id,
                   "system_prompt": prompt_text if prompt_text is not None else (PROMPTS / (prompt_version + ".txt")).read_text(encoding="utf-8"),
                   "prompt_version": prompt_version, "payload": payload,
                   "sample_seed": int(digest([self.seed, call_id])[:8], 16),
                   "model": {"model_id": model.model_id, "temperature": model.temperature,
                             "supports_seed": model.supports_seed},
                   "limits": {"max_output_tokens": max_output_tokens or self.budget.max_output_tokens,
                              "max_total_tokens": total_token_allowance}}
        request_hash = digest(request)
        context = dict(block_id=block_id, branch_id=branch_id, phase=phase, actor=role)
        cached = self.cache.get(call_id)
        if cached:
            require(cached["request_hash"] == request_hash, "Resume payload differs from recorded request")
            if cached["kind"] == "call_failure":
                raise RecordedFailure(f"Recorded terminal failure for {call_id}: {cached['error']}")
            return validator(cached["response"]["output"]), cached["response"]["usage"]
        if len(canonical(request).encode("utf-8")) > self.budget.max_context_bytes:
            self._fail(call_id, request_hash, "Context byte budget exceeded", context)
            raise BudgetExceeded("Context byte budget exceeded")
        prior_attempts = sum(e["kind"] == "call_attempt" and e.get("call_id") == call_id
                             for e in self.journal.events)
        for attempt in range(prior_attempts + 1, self.budget.transport_attempts + 1):
            self.journal.append("call_attempt", **context, call_id=call_id, request_hash=request_hash,
                                request=request, model_metadata=asdict(model), attempt=attempt,
                                retry_count=attempt - 1)
            started = time.monotonic()
            try:
                response = self.transports[model.adapter].generate(request, model)
            except TransportError as exc:
                self.journal.append("transport_failure", **context, call_id=call_id, attempt=attempt,
                                    latency_ms=round((time.monotonic() - started) * 1000),
                                    status="transport_error", error=str(exc))
                if attempt < self.budget.transport_attempts:
                    time.sleep(min(2 ** (attempt - 1), 4))
                    continue
                self._fail(call_id, request_hash, str(exc), context)
                raise
            except ValidationError as exc:
                self._fail(call_id, request_hash, str(exc), context)
                raise
            try:
                keys(response, {"output", "usage", "provider_request_id", "model_id", "tool_calls"})
                keys(response["usage"], {"input_tokens", "output_tokens", "estimated"})
                for name in ("input_tokens", "output_tokens"):
                    integer(response["usage"][name], name)
                require(type(response["usage"]["estimated"]) is bool, "estimated must be boolean")
                string(response["provider_request_id"], "provider_request_id")
                require(response["model_id"] == model.model_id, "Adapter returned a different model ID")
                require(response["tool_calls"] == [], "Protocol v1 disables model tools")
                output = validator(response["output"])
                usage = response["usage"]
                require(usage["output_tokens"] <= request["limits"]["max_output_tokens"], "Output token cap exceeded")
                if total_token_allowance is not None:
                    require(usage["input_tokens"] + usage["output_tokens"] <= total_token_allowance,
                            "Coaching token cap exceeded")
            except (ValidationError, TypeError, KeyError) as exc:
                self._fail(call_id, request_hash, str(exc), context, response=response,
                           latency_ms=round((time.monotonic() - started) * 1000), attempt=attempt)
                raise ValidationError(str(exc)) from exc
            event = self.journal.append("call_result", **context, call_id=call_id,
                                        request_hash=request_hash, response=response, usage=usage,
                                        latency_ms=round((time.monotonic() - started) * 1000),
                                        attempt=attempt, retry_count=attempt - 1)
            self.cache[call_id] = event
            return output, usage
        self._fail(call_id, request_hash, "Transport attempt budget exhausted", context)
        raise RecordedFailure("Transport attempt budget exhausted")

    def _fail(self, call_id, request_hash, error, context, **details):
        event = self.journal.append("call_failure", **context, call_id=call_id,
                                    request_hash=request_hash, error=error, status="failed", **details)
        self.cache[call_id] = event
