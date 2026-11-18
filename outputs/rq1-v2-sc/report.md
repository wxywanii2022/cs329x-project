# RQ1 Main 1: local assessor vs human reference

Adjudicated reference: {'N/A': 42, '2': 13, '0': 4, '1': 1}. Agreement over successful pairs; 95% bootstrap intervals (10000 item resamples). Primary run = seed 329.

| Comparison | n | Raw agreement | Cohen's κ | False-missed rate |
|---|---|---|---|---|
| Human A vs B (pre-adjudication) | 59 | 0.780 [0.68, 0.88] | 0.590 [0.40, 0.76] | 0.056 [0.00, 0.12] (3/54) |
| Human A vs adjudicated | 60 | 0.933 [0.87, 0.98] | 0.863 [0.72, 0.97] | 0.036 [0.00, 0.09] (2/56) |
| Human B vs adjudicated | 59 | 0.847 [0.75, 0.93] | 0.702 [0.53, 0.86] | 0.036 [0.00, 0.09] (2/55) |
| qwen38-27b-fp8 s329 (primary) vs adjudicated | 60 | 0.817 [0.72, 0.90] | 0.652 [0.47, 0.81] | 0.089 [0.02, 0.17] (5/56) |
| qwen38-27b-fp8 s329 (primary) vs A | 60 | 0.883 [0.80, 0.95] | 0.788 [0.63, 0.91] | 0.055 [0.00, 0.12] (3/55) |
| qwen38-27b-fp8 s329 (primary) vs B | 59 | 0.814 [0.71, 0.92] | 0.673 [0.49, 0.83] | 0.093 [0.02, 0.18] (5/54) |

## qwen38-27b-fp8

`Qwen/Qwen3.8-27B-FP8@017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 0 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768; output contract decision-point-v2.

- seed 329: coverage 60/60, failed 0, pending 0, labels {'N/A': 36, '2': 12, '0': 7, '1': 5}, median output tokens 1411.0, median latency 51.303 s

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 2 | 2 | 0 | 0 |
| **1** | 0 | 1 | 0 | 0 |
| **2** | 0 | 1 | 11 | 1 |
| **N/A** | 5 | 1 | 1 | 35 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 15 | 0.800 | 0.690 | 0 |
| B2 | 15 | 0.800 | 0.571 | 2 |
| B3 | 15 | 0.733 | 0.412 | 3 |
| B4 | 15 | 0.933 | 0.634 | 0 |

On items where A and B agreed: 46 items, raw 0.957. Where they disagreed: 13 items, raw 0.308.

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M1-005 | B3 | N/A | 0 | N/A | 0 | high | The user asks only to open the produced file rather than selecting or checking any substantive claim in the agent's summary. |
| M1-016 | B2 | N/A | 2 | N/A | 2 | medium | The request explicitly requires a calculation of FSC space used versus available, which is a usable calculation requirement. |
| M1-026 | B3 | 0 | 0 | 1 | 1 | medium | The user requests a broad review of conclusory and criminal-conduct language without selecting a particular claim to verify. |
| M1-027 | B2 | N/A | N/A | N/A | 0 | medium | The user reports a runtime module-not-found error but does not state any source, calculation, or evidence standard for the requested diagnosis or fix. |
| M1-030 | B1 | N/A | N/A | 1 | 1 | medium | The turn requests moving the existing documents to a named Desktop folder, giving one concrete delivery-location constraint but no second deliverable property. |
| M1-031 | B4 | 2 | 2 | N/A | N/A | high | Turn 44 is a simple approval of the agent's proposed log-tab design, with no problem in any produced output identified or corrected. |
| M1-034 | B2 | N/A | N/A | 1 | 0 | medium | The revision request asks for factual completeness but does not state a usable source, citation, or calculation standard for supporting the figures. |
| M1-044 | B3 | N/A | 0 | N/A | 0 | high | The assistant made a checkable claim that the poster was regenerated as a professional four-column layout, but the user did not ask it to be checked and instead proposed a font-size change. |
| M1-046 | B3 | N/A | N/A | N/A | 0 | medium | The user moved on to a new request without checking the agent's claim that PowerPoint generation was unavailable and a Markdown outline was provided. |
| M1-047 | B1 | 2 | 2 | 1 | 1 | medium | The new-output request names a preferred PDF format and a vague conversation snapshot, but does not state two clearly concrete output properties. |
| M1-055 | B1 | 0 | 1 | 0 | 1 | medium | The opening request names a slideshow as the deliverable but gives no additional concrete requirements. |
