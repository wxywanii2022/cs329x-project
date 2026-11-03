"""Lexical wiring fixture ONLY. Not calibrated, not a learner/assessor model."""
import re


def mock_annotation(payload):
    messages = payload["messages"]
    behavior = payload["behavior"]
    label, status = None, "insufficient_evidence"
    if messages:
        text = messages[-1]["content"].lower()
        prefix = "\n".join(m["content"] for m in messages[:-1]).lower()
        numeric = bool(re.search(r"\d", prefix))
        status = "available"
        if behavior == "B1":
            properties = sum(any(term in text for term in group) for group in (
                ("manager", "director"), ("one page", "one-page", "half-page"),
                ("three bullets", "three-bullet", "two-bullet")))
            label = 2 if properties >= 2 else 1 if properties or "professional" in text else 0
            if "prefer" in text:
                label, status = None, "no_opportunity"
        elif behavior == "B2":
            label = 2 if any(t in text for t in ("source column", "source table", "calculation")) else 1 if "accur" in text else 0
            if "prefer" in text and not numeric:
                label, status = None, "no_opportunity"
        elif behavior == "B3":
            claim = any(m["role"] == "assistant" and re.search(r"\d+\s*%", m["content"]) for m in messages[:-1])
            if claim:
                targeted = bool(re.search(r"verif|check|recalcul|confirm|where|how|correct|wrong", text) and re.search(r"growth|increase|percent|\d\s*%", text))
                label = 2 if targeted else 1 if "check" in text else 0
            else:
                label, status = None, "no_opportunity"
        else:
            if "conflicts with the table" in prefix:
                label = 2 if re.search(r"correct|fix|replace|revise", text) and re.search(r"\d+\s*%", text) else 1 if any(t in text for t in ("wrong", "fix", "error")) else 0
            else:
                label, status = None, "no_opportunity"
    return {"behavior": behavior, "label": label, "opportunity_status": status,
            "na_reason": status if label is None else None,
            "reason": "Offline lexical fixture; this is not a validated assessment.",
            "confidence": "low", "unclear_rule": "",
            "evidence": [{"turn_id": messages[-1]["turn_id"], "quote": messages[-1]["content"][:500]}] if messages else []}
