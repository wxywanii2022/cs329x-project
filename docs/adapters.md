# Role adapter contract (version 1)

The runner owns routing, persistent history, branch isolation and scoring exports. An adapter performs one model invocation using only its supplied role payload. It must not read other run files, reuse another role's conversation, invent a learning update, or add hidden condition information. A process boundary is an interface boundary, not an OS security sandbox: trusted team adapter code is responsible for obeying it.

## Process protocol

Configure a model as:

```json
{
  "adapter": "command",
  "model_id": "your-exact-accessible-model-id",
  "family": "your-actual-model-lineage",
  "command": ["python", "path/to/your_adapter.py"],
  "temperature": 0.7,
  "supports_seed": false,
  "timeout_seconds": 120
}
```

Use an absolute interpreter path when `python` is not on PATH. Paths resolve from the invocation's working directory. No shell expansion occurs. A new process receives one UTF-8 JSON object on stdin and emits exactly one JSON object on stdout; put diagnostics on stderr and never include credentials. The runner deliberately does not copy arbitrary stderr to its journal.

Request envelope:

```json
{
  "protocol_version": "1",
  "role": "learner",
  "session_id": "opaque-session-id",
  "system_prompt": "Versioned role prompt ...",
  "prompt_version": "learner_v1",
  "payload": {},
  "sample_seed": 12345,
  "model": {"model_id": "exact-id", "temperature": 0.7, "supports_seed": false},
  "limits": {"max_output_tokens": 700, "max_total_tokens": null}
}
```

`sample_seed` is always recorded for reproducibility; send it to a provider only when `supports_seed` is true. It does not promise determinism across services. Session IDs and the role name are routing metadata, not text to inject into a learner conversation. Model input consists of the versioned system prompt and the masked payload.

Response envelope:

```json
{
  "output": {"content": "Please check the growth percentage against the table."},
  "usage": {"input_tokens": 300, "output_tokens": 20, "estimated": false},
  "provider_request_id": "provider-request-id",
  "model_id": "exact-id",
  "tool_calls": []
}
```

All fields are required. `model_id` must equal the configured ID. Nonnegative integer usage is required. Report provider counts when available; mark estimates honestly. The runner validates output shape, evidence, usage, and model identity before accepting it. Tool calls are forbidden in version 1 so access is identical across conditions.

Exit **75** only for temporary transport/rate-limit failures that are appropriate to retry. Other nonzero exits are terminal. Do not retry internally: the runner owns retries and logs every attempt. Invalid or inconvenient substantive behavior must not be regenerated. Transport-failure token charges may be unknown.

`examples/mock_command_adapter.py` is a functioning offline round-trip example. Its behavior remains a mock even if invoked with `adapter: command`; using a process does not make it a research model.

## Input/output by role

| Role | Payload fields | Output |
| --- | --- | --- |
| Learner | `initial_background`, `observed_history`, `task`, `stage` | `{"content": "visible learner message"}` |
| Assessment | `task`, `messages`, `opportunities`, `rubric_version` | `{"items": [B1, B2, B3, B4]}` |
| Coach | `task`, `messages`, `exercise_bank`, optional permitted `assessment` and `background` | One decision below |
| Evaluator | `blind_record_id`, `task`, `messages`, `opportunities`, `answer_key`, `final_artifact`, `rubric_version` | `{"items": [B1, B2, B3, B4]}` |

The learner receives dated starting knowledge without profile IDs or novice/intermediate/expert labels. `stage` is `request`, `review`, `correction`, or `practice`. Practice is observable coaching, not a hidden experimental label. History is only what that learner has observed; it contains no answer-key object, evaluator feedback, or assessment labels.

Assessment is background-blind and must respect the recorded decision point. It can compute from publicly available source tables but never receives the private answer key. Replace its prompt and adapter with the team's validated RQ1 module; do not rename the candidate prompt and claim it is validated.

Coach output:

```json
{
  "action": "exercise",
  "exercise_id": "check_v1",
  "target_behavior": "B3",
  "brief_rationale": "The visible request did not target a specific claim."
}
```

For `action: none`, both ID and target must be null. IDs must exist in the supplied bank and targets must match them. The runner, not the selector, delivers the selected exercise's fixed messages. There is no second selection call or switch to another exercise. This MVP uses one fixed sequence per exercise; adaptive feedback can be added only as a shared, versioned execution policy.

Score item:

```json
{
  "behavior_id": "B3",
  "opportunity_status": "available",
  "label": 2,
  "na_reason": null,
  "evidence_message_ids": ["m004"],
  "supporting_spans": ["Please verify the growth percentage"],
  "brief_rationale": "The learner selected the growth claim for a calculation check."
}
```

There must be exactly one item per B1–B4. Non-null labels need evidence. Spans must be exact nonempty substrings, at most 500 characters each, aligned one-to-one with message IDs. Evidence cannot use a message after that behavior's designated decision point. Null uses a matching `opportunity_status` and `na_reason` of `no_opportunity` or `insufficient_evidence`; empty evidence lists are allowed for N/A. A scorer cannot silently change the runner's recorded opportunity status.

The four primary task scores aggregate four predesignated decision points. They are not an arbitrary conversation-wide maximum and are not general annotations of every turn.

## HTTP bridge

The included `python -m adaptive_tutor.adapters.http_bridge` translates this protocol to one HTTPS Chat Completions request. It uses JSON object response mode with application-level strict validation, no tools, `store: false`, and `max_completion_tokens`. Its request fields follow the [official API reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create). Native provider APIs with a different schema need their own process adapter.

Set per role:

```powershell
$env:TUTOR_LEARNER_URL = 'https://your-provider.example/v1/chat/completions'
$env:TUTOR_LEARNER_API_KEY = '<set locally; never commit>'
# Also set TUTOR_ASSESSMENT_*, TUTOR_COACH_*, TUTOR_EVALUATOR_*.
```

URLs and credentials are environment configuration, not model prompts. For reproducible operational records, keep a private note of the endpoints used, without keys. Provider model IDs, family declarations, prompts, requests, sampling and returned request IDs are logged by the runner. Network behavior and real model compatibility have not been exercised by the offline tests.

The bridge sends temperature and optional seed only as configured; it does not silently remove unsupported parameters or substitute models. Its provider timeout is 90 seconds, below the default process timeout of 120 seconds. It treats HTTP 408/429/500/502/503/504 and network failures as retryable. Redirects are disabled to avoid forwarding credentials. Input usage is known only after a response, so the total token cap cannot guarantee a billing ceiling.
