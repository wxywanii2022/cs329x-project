# RQ1 Main 1: local assessor vs human reference

Adjudicated reference: {'N/A': 42, '2': 13, '0': 4, '1': 1}. Agreement over successful pairs; 95% bootstrap intervals (10000 item resamples). Primary run = seed 329.

| Comparison | n | Raw agreement | Cohen's κ | False-missed rate |
|---|---|---|---|---|
| Human A vs B (pre-adjudication) | 59 | 0.780 [0.68, 0.88] | 0.590 [0.40, 0.76] | 0.056 [0.00, 0.12] |
| Human A vs adjudicated | 60 | 0.933 [0.87, 0.98] | 0.863 [0.72, 0.97] | 0.036 [0.00, 0.09] |
| Human B vs adjudicated | 59 | 0.847 [0.75, 0.93] | 0.702 [0.53, 0.86] | 0.036 [0.00, 0.09] |
| qwen35-9b s329 (primary) vs adjudicated | 59 | 0.814 [0.71, 0.90] | 0.580 [0.35, 0.77] | 0.073 [0.02, 0.15] |
| qwen35-9b s329 (primary) vs A | 59 | 0.814 [0.71, 0.90] | 0.609 [0.39, 0.79] | 0.056 [0.00, 0.12] |
| qwen35-9b s329 (primary) vs B | 58 | 0.776 [0.66, 0.88] | 0.550 [0.34, 0.74] | 0.075 [0.02, 0.15] |
| qwen35-9b s330 (seed) vs adjudicated | 57 | 0.860 [0.77, 0.95] | 0.702 [0.51, 0.87] | 0.038 [0.00, 0.10] |
| qwen35-9b s330 (seed) vs A | 57 | 0.842 [0.74, 0.93] | 0.685 [0.49, 0.85] | 0.038 [0.00, 0.10] |
| qwen35-9b s330 (seed) vs B | 56 | 0.804 [0.70, 0.91] | 0.618 [0.42, 0.80] | 0.059 [0.00, 0.13] |
| qwen35-9b s331 (seed) vs adjudicated | 59 | 0.847 [0.75, 0.93] | 0.671 [0.47, 0.84] | 0.036 [0.00, 0.09] |
| qwen35-9b s331 (seed) vs A | 59 | 0.814 [0.71, 0.90] | 0.623 [0.41, 0.80] | 0.037 [0.00, 0.09] |
| qwen35-9b s331 (seed) vs B | 58 | 0.759 [0.64, 0.86] | 0.531 [0.35, 0.70] | 0.038 [0.00, 0.10] |
| qwen38-27b-fp8 s329 (primary) vs adjudicated | 60 | 0.833 [0.73, 0.92] | 0.688 [0.50, 0.85] | 0.107 [0.04, 0.19] |
| qwen38-27b-fp8 s329 (primary) vs A | 60 | 0.900 [0.82, 0.97] | 0.820 [0.66, 0.94] | 0.073 [0.02, 0.15] |
| qwen38-27b-fp8 s329 (primary) vs B | 59 | 0.780 [0.68, 0.88] | 0.618 [0.45, 0.77] | 0.130 [0.05, 0.23] |
| qwen38-27b-fp8 s330 (seed) vs adjudicated | 60 | 0.850 [0.75, 0.93] | 0.708 [0.53, 0.86] | 0.054 [0.00, 0.12] |
| qwen38-27b-fp8 s330 (seed) vs A | 60 | 0.883 [0.80, 0.97] | 0.784 [0.62, 0.92] | 0.036 [0.00, 0.09] |
| qwen38-27b-fp8 s330 (seed) vs B | 59 | 0.831 [0.73, 0.92] | 0.696 [0.52, 0.85] | 0.056 [0.00, 0.13] |
| qwen38-27b-fp8 s331 (seed) vs adjudicated | 60 | 0.850 [0.75, 0.93] | 0.712 [0.53, 0.87] | 0.071 [0.02, 0.15] |
| qwen38-27b-fp8 s331 (seed) vs A | 60 | 0.917 [0.85, 0.98] | 0.847 [0.70, 0.97] | 0.036 [0.00, 0.09] |
| qwen38-27b-fp8 s331 (seed) vs B | 59 | 0.780 [0.68, 0.88] | 0.610 [0.43, 0.77] | 0.093 [0.02, 0.17] |

## qwen35-9b

`Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 1.5 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768; output contract decision-point-v2.

- seed 329: completed 59/60, failed 1, labels {'N/A': 43, '2': 9, '0': 5, '1': 2}, median output tokens 3594, median latency 92.116 s
  - post-hoc (not pre-declared), also scoring the 1 outputs that failed only the exact-quote check: n 60, raw 0.800 [0.70, 0.90], κ 0.554 [0.33, 0.75], false-missed 0.071 [0.02, 0.15]
  - 1 failed: Evidence quote not in cited turn
- seed 330: completed 57/60, failed 3, labels {'N/A': 40, '2': 11, '0': 4, '1': 2}, median output tokens 3062, median latency 79.393 s
  - post-hoc (not pre-declared), also scoring the 2 outputs that failed only the exact-quote check: n 59, raw 0.847 [0.75, 0.93], κ 0.673 [0.48, 0.84], false-missed 0.036 [0.00, 0.09]
  - 2 failed: Evidence quote not in cited turn
  - 1 failed: Missing keys: {'na_reason', 'label', 'unclear_rule', 'opportunity_status', 'reason', 'behavior', 'evidence', 'confidence
- seed 331: completed 59/60, failed 1, labels {'N/A': 42, '2': 10, '0': 3, '1': 4}, median output tokens 1421, median latency 37.668 s
  - post-hoc (not pre-declared), also scoring the 1 outputs that failed only the exact-quote check: n 60, raw 0.850 [0.75, 0.93], κ 0.672 [0.47, 0.85], false-missed 0.036 [0.00, 0.09]
  - 1 failed: Evidence quote not in cited turn

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 1 | 1 | 0 | 2 |
| **1** | 0 | 0 | 0 | 1 |
| **2** | 0 | 1 | 9 | 2 |
| **N/A** | 4 | 0 | 0 | 38 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 15 | 0.800 | 0.672 | 0 |
| B2 | 14 | 0.857 | 0.440 | 1 |
| B3 | 15 | 0.800 | 0.286 | 1 |
| B4 | 15 | 0.800 | 0.328 | 2 |

On items where A and B agreed: 45 items, raw 0.911. Where they disagreed: 13 items, raw 0.462.

Seed stability ([329, 330, 331]): 45/56 items unanimous; mean pairwise κ 0.699; unstable: M1-005, M1-017, M1-026, M1-034, M1-035, M1-037, M1-038, M1-041, M1-044, M1-047, M1-048. Majority-of-seeds vs adjudicated (secondary): raw 0.839, κ 0.634, false-missed 0.038.

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M1-005 | B3 | N/A | 0 | N/A | 0 | high | User requests to open a file, which is a delivery question without a substantive claim to verify. |
| M1-026 | B3 | 0 | 0 | 1 | N/A | high | turn 28 provides revision guidelines rather than selecting a specific claim to verify |
| M1-031 | B4 | 2 | 2 | N/A | N/A | high | User accepts recommendation without addressing a visible output problem |
| M1-035 | B2 | N/A | N/A | N/A | 0 | high | User requested a comprehensive analysis but provided no specific requirements for data sources, evidence verification, or citations. |
| M1-037 | B4 | N/A | N/A | N/A | 0 | medium | A visible output problem exists (agent claims to have drafted sections without providing the requested document content), but the user's turn ('print') does not address or attempt to correct it. |
| M1-038 | B2 | 2 | 2 | 2 | N/A | high | User requests column layout and EBITDA definition clarification, but does not specify evidence requirements for factual claims |
| M1-040 | B4 | N/A | N/A | 1 | 0 | high | User requests conversion of a file to a new format and destination without addressing prior output discrepancies or errors. |
| M1-041 | B3 | 0 | 0 | 0 | N/A | medium | User requests HTML formatting conversion without checking or selecting any substantive claim from the agent's prior output |
| M1-047 | B1 | 2 | 2 | 1 | 1 | high | User specifies a format (PDF) for the conversation but lacks additional concrete output constraints like length or audience. |
| M1-048 | B1 | 1 | 1 | 0 | N/A | high | user asks generic testing advice without specifying output format, structure, depth, or other deliverable requirements |
| M1-055 | B1 | 0 | 1 | 0 | 1 | medium | The user specifies the output format as a slideshow but provides only one concrete property without additional constraints. |

## qwen38-27b-fp8

`Qwen/Qwen3.8-27B-FP8@017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 0 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768; output contract decision-point-v2.

- seed 329: completed 60/60, failed 0, labels {'N/A': 35, '2': 13, '0': 9, '1': 3}, median output tokens 1377.0, median latency 56.581 s
- seed 330: completed 60/60, failed 0, labels {'N/A': 37, '2': 13, '0': 5, '1': 5}, median output tokens 1550.5, median latency 65.190 s
- seed 331: completed 60/60, failed 0, labels {'N/A': 36, '2': 14, '0': 7, '1': 3}, median output tokens 1391.5, median latency 59.238 s

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 3 | 1 | 0 | 0 |
| **1** | 0 | 1 | 0 | 0 |
| **2** | 0 | 0 | 12 | 1 |
| **N/A** | 6 | 1 | 1 | 34 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 15 | 0.867 | 0.783 | 0 |
| B2 | 15 | 0.733 | 0.487 | 3 |
| B3 | 15 | 0.867 | 0.667 | 2 |
| B4 | 15 | 0.867 | 0.444 | 1 |

On items where A and B agreed: 46 items, raw 0.957. Where they disagreed: 13 items, raw 0.385.

Seed stability ([329, 330, 331]): 50/60 items unanimous; mean pairwise κ 0.806; unstable: M1-005, M1-026, M1-027, M1-031, M1-034, M1-035, M1-040, M1-046, M1-047, M1-060. Majority-of-seeds vs adjudicated (secondary): raw 0.850, κ 0.713, false-missed 0.089.

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M1-005 | B3 | N/A | 0 | N/A | 0 | medium | The user asks only to open the saved file and does not select or verify any prior substantive claim. |
| M1-016 | B2 | N/A | 2 | N/A | 2 | medium | The request asks for a specific calculation comparing FSC space used with available space. |
| M1-027 | B2 | N/A | N/A | N/A | 0 | medium | The user reports a local test failure and implicitly requests troubleshooting but provides no source, calculation, or verification standard for the assistant's explanation. |
| M1-030 | B1 | N/A | N/A | 1 | 1 | medium | The user specifies a single concrete delivery constraint, the destination folder for the existing documents. |
| M1-031 | B4 | 2 | 2 | N/A | N/A | high | The user merely approves the assistant's proposal to build a simple log tab, with no specific problem in an agent output to correct. |
| M1-034 | B2 | N/A | N/A | 1 | 0 | medium | The user requests a factual expanded constituent dataset with a date but does not specify a source, calculation, or audit trail for supporting the revised figures. |
| M1-035 | B2 | N/A | N/A | N/A | 0 | medium | The turn requests an analysis but gives no usable source, calculation, or justification requirement. |
| M1-040 | B4 | N/A | N/A | 1 | 0 | medium | The user makes a new PDF conversion request without identifying or correcting the earlier file-location contradiction. |
| M1-044 | B3 | N/A | 0 | N/A | 0 | medium | The user does not select or verify a checkable agent claim, but instead requests a further design change. |
| M1-055 | B1 | 0 | 1 | 0 | 1 | medium | The request names a deliverable format but gives no other concrete requirements such as length, audience, or content. |
