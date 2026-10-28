"""Executable JSON-over-stdio adapter example; intentionally still an offline mock.

Use an absolute interpreter path in config.command if `python` is not on PATH.
"""

import json
import sys

from adaptive_tutor.adapters.mock import MockAdapter
from adaptive_tutor.schema import ModelSpec

request = json.load(sys.stdin)
model = ModelSpec(adapter="mock", model_id=request["model"]["model_id"], family="mock")
json.dump(MockAdapter().generate(request, model), sys.stdout)
