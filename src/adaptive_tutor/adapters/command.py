"""Provider-independent JSON-over-stdio integration; credentials stay in the environment."""

import json
import subprocess

from ..schema import ValidationError
from ..storage import canonical


class TransportError(RuntimeError):
    pass


class CommandAdapter:
    def generate(self, request: dict, model) -> dict:
        try:
            result = subprocess.run(list(model.command), input=canonical(request),
                                    capture_output=True, text=True, encoding="utf-8",
                                    timeout=model.timeout_seconds, shell=False, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise TransportError(type(exc).__name__) from exc
        # EX_TEMPFAIL signals a retryable provider transport failure. Other exits
        # are terminal. Never copy arbitrary stderr (possibly secrets) into logs.
        if result.returncode == 75:
            raise TransportError("adapter reported a temporary transport failure (exit 75)")
        if result.returncode:
            raise ValidationError(f"Adapter exited {result.returncode}; inspect its local diagnostics")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ValidationError("Adapter did not return one valid JSON object") from exc
