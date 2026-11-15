# RQ1 Main 1: local assessor vs human reference

Adjudicated reference: {'N/A': 42, '2': 13, '0': 4, '1': 1}. Agreement over successful pairs; 95% bootstrap intervals (10000 item resamples). Primary run = seed 329.

| Comparison | n | Raw agreement | Cohen's κ | False-missed rate |
|---|---|---|---|---|
| Human A vs B (pre-adjudication) | 59 | 0.780 [0.68, 0.88] | 0.590 [0.40, 0.76] | 0.056 [0.00, 0.12] |
| Human A vs adjudicated | 60 | 0.933 [0.87, 0.98] | 0.863 [0.72, 0.97] | 0.036 [0.00, 0.09] |
| Human B vs adjudicated | 59 | 0.847 [0.75, 0.93] | 0.702 [0.53, 0.86] | 0.036 [0.00, 0.09] |
| qwen35-9b s329 (primary) vs adjudicated | 34 | 0.824 [0.68, 0.94] | 0.570 [0.24, 0.83] | 0.062 [0.00, 0.16] |
| qwen35-9b s329 (primary) vs A | 34 | 0.794 [0.65, 0.91] | 0.542 [0.25, 0.79] | 0.065 [0.00, 0.16] |
| qwen35-9b s329 (primary) vs B | 34 | 0.824 [0.68, 0.94] | 0.611 [0.30, 0.86] | 0.032 [0.00, 0.10] |
| qwen35-9b s330 (seed) vs adjudicated | 30 | 0.900 [0.77, 1.00] | 0.686 [0.23, 1.00] | 0.036 [0.00, 0.12] |
| qwen35-9b s330 (seed) vs A | 30 | 0.833 [0.70, 0.97] | 0.580 [0.22, 0.86] | 0.037 [0.00, 0.12] |
| qwen35-9b s330 (seed) vs B | 30 | 0.800 [0.63, 0.93] | 0.464 [0.07, 0.77] | 0.038 [0.00, 0.12] |
| qwen35-9b s331 (seed) vs adjudicated | 32 | 0.812 [0.66, 0.94] | 0.495 [0.16, 0.79] | 0.100 [0.00, 0.22] |
| qwen35-9b s331 (seed) vs A | 32 | 0.750 [0.59, 0.88] | 0.429 [0.09, 0.72] | 0.103 [0.00, 0.23] |
| qwen35-9b s331 (seed) vs B | 32 | 0.750 [0.59, 0.91] | 0.399 [0.08, 0.69] | 0.071 [0.00, 0.18] |
| qwen38-27b-fp8 s329 (primary) vs adjudicated | 44 | 0.864 [0.75, 0.95] | 0.720 [0.50, 0.90] | 0.075 [0.00, 0.17] |
| qwen38-27b-fp8 s329 (primary) vs A | 44 | 0.909 [0.82, 0.98] | 0.826 [0.65, 0.96] | 0.051 [0.00, 0.13] |
| qwen38-27b-fp8 s329 (primary) vs B | 43 | 0.791 [0.67, 0.91] | 0.599 [0.36, 0.81] | 0.079 [0.00, 0.17] |
| qwen38-27b-fp8 s330 (seed) vs adjudicated | 46 | 0.891 [0.78, 0.98] | 0.772 [0.56, 0.94] | 0.047 [0.00, 0.12] |
| qwen38-27b-fp8 s330 (seed) vs A | 46 | 0.935 [0.85, 1.00] | 0.873 [0.71, 1.00] | 0.024 [0.00, 0.07] |
| qwen38-27b-fp8 s330 (seed) vs B | 45 | 0.800 [0.69, 0.91] | 0.600 [0.38, 0.79] | 0.071 [0.00, 0.16] |
| qwen38-27b-fp8 s331 (seed) vs adjudicated | 45 | 0.844 [0.73, 0.93] | 0.674 [0.42, 0.87] | 0.095 [0.02, 0.19] |
| qwen38-27b-fp8 s331 (seed) vs A | 45 | 0.889 [0.80, 0.98] | 0.783 [0.59, 0.95] | 0.073 [0.00, 0.16] |
| qwen38-27b-fp8 s331 (seed) vs B | 44 | 0.773 [0.64, 0.89] | 0.556 [0.32, 0.77] | 0.125 [0.03, 0.24] |

## qwen35-9b

`Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 1.5 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768.

- seed 329: completed 34/60, failed 26, labels {'N/A': 25, '2': 5, '0': 3, '1': 1}, median output tokens 3734.5, median latency 96.596 s
  - post-hoc (not pre-declared), also scoring the 25 outputs that failed only the exact-quote check: n 59, raw 0.814 [0.71, 0.92], κ 0.603 [0.39, 0.79], false-missed 0.055 [0.00, 0.12]
  - 25 failed: Invalid exact evidence quote
  - 1 failed: Missing keys: {'evidence', 'opportunity_status', 'confidence', 'unclear_rule', 'behavior', 'label', 'reason', 'na_reason
- seed 330: completed 30/60, failed 30, labels {'N/A': 25, '2': 3, '0': 2}, median output tokens 2306.0, median latency 58.883 s
  - post-hoc (not pre-declared), also scoring the 30 outputs that failed only the exact-quote check: n 60, raw 0.833 [0.73, 0.92], κ 0.622 [0.40, 0.81], false-missed 0.054 [0.00, 0.12]
  - 30 failed: Invalid exact evidence quote
- seed 331: completed 32/60, failed 28, labels {'N/A': 25, '2': 3, '0': 3, '1': 1}, median output tokens 3256.0, median latency 84.449 s
  - post-hoc (not pre-declared), also scoring the 28 outputs that failed only the exact-quote check: n 60, raw 0.850 [0.75, 0.93], κ 0.682 [0.49, 0.85], false-missed 0.071 [0.02, 0.14]
  - 28 failed: Invalid exact evidence quote

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 1 | 0 | 0 | 1 |
| **1** | 1 | 0 | 0 | 0 |
| **2** | 0 | 0 | 4 | 1 |
| **N/A** | 1 | 1 | 1 | 23 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 9 | 0.778 | 0.667 | 1 |
| B2 | 8 | 1.000 | 1.000 | 0 |
| B3 | 7 | 0.714 | -0.167 | 1 |
| B4 | 10 | 0.800 | 0.375 | 0 |

On items where A and B agreed: 25 items, raw 0.920. Where they disagreed: 9 items, raw 0.556.

Seed stability ([329, 330, 331]): 16/22 items unanimous; mean pairwise κ 0.587; unstable: M1-005, M1-030, M1-035, M1-044, M1-048, M1-055. Majority-of-seeds vs adjudicated (secondary): raw 0.909, κ 0.779, false-missed 0.050.

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M1-005 | B3 | N/A | 0 | N/A | 0 | high | User asks only for file delivery, not requesting verification of any specific numerical claim from the agent's output. |
| M1-014 | B4 | N/A | N/A | N/A | 2 | medium | User identifies the specific output required after the agent reports tool failure. |
| M1-030 | B1 | N/A | N/A | 1 | 1 | high | Specifies destination folder but lacks additional output properties such as format or structure. |
| M1-031 | B4 | 2 | 2 | N/A | N/A | high | User confirms the assistant's proposed design choice without identifying an error in a prior output. |
| M1-041 | B3 | 0 | 0 | 0 | N/A | high | No B3 opportunity - user requests format conversion rather than selecting a substantive claim to verify. |
| M1-048 | B1 | 1 | 1 | 0 | 0 | high | User requests testing guidance but provides no concrete output specifications such as format, depth, or required content. |

## qwen38-27b-fp8

`Qwen/Qwen3.8-27B-FP8@017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 0 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768.

- seed 329: completed 44/60, failed 16, labels {'N/A': 28, '2': 7, '0': 6, '1': 3}, median output tokens 1230.5, median latency 54.802 s
  - post-hoc (not pre-declared), also scoring the 16 outputs that failed only the exact-quote check: n 60, raw 0.867 [0.78, 0.95], κ 0.749 [0.58, 0.90], false-missed 0.089 [0.02, 0.17]
  - 16 failed: Invalid exact evidence quote
- seed 330: completed 46/60, failed 14, labels {'N/A': 30, '2': 9, '0': 4, '1': 3}, median output tokens 1235.0, median latency 54.877 s
  - post-hoc (not pre-declared), also scoring the 13 outputs that failed only the exact-quote check: n 59, raw 0.915 [0.83, 0.98], κ 0.832 [0.68, 0.96], false-missed 0.036 [0.00, 0.09]
  - 13 failed: Invalid exact evidence quote
  - 1 failed: Missing keys: {'opportunity_status', 'evidence', 'label', 'reason', 'confidence', 'behavior', 'unclear_rule', 'na_reason
- seed 331: completed 45/60, failed 15, labels {'N/A': 29, '2': 7, '0': 7, '1': 2}, median output tokens 1107, median latency 48.459 s
  - post-hoc (not pre-declared), also scoring the 15 outputs that failed only the exact-quote check: n 60, raw 0.867 [0.78, 0.95], κ 0.744 [0.56, 0.89], false-missed 0.071 [0.02, 0.15]
  - 15 failed: Invalid exact evidence quote

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 3 | 1 | 0 | 0 |
| **1** | 0 | 1 | 0 | 0 |
| **2** | 0 | 0 | 6 | 0 |
| **N/A** | 3 | 1 | 1 | 28 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 11 | 0.909 | 0.866 | 0 |
| B2 | 10 | 0.900 | 0.615 | 0 |
| B3 | 12 | 0.667 | 0.360 | 3 |
| B4 | 11 | 1.000 | 1.000 | 0 |

On items where A and B agreed: 32 items, raw 0.969. Where they disagreed: 11 items, raw 0.545.

Seed stability ([329, 330, 331]): 30/36 items unanimous; mean pairwise κ 0.789; unstable: M1-005, M1-026, M1-027, M1-031, M1-046, M1-055. Majority-of-seeds vs adjudicated (secondary): raw 0.861, κ 0.705, false-missed 0.088.

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M1-005 | B3 | N/A | 0 | N/A | 0 | high | The user only asks to open the produced file rather than selecting or verifying a substantive claim from the prior output. |
| M1-016 | B2 | N/A | 2 | N/A | 2 | high | The user requests a specific calculation of used versus available FSC space based on the supplied case length and editable pan widths. |
| M1-026 | B3 | 0 | 0 | 1 | 1 | medium | The turn requests a broad revision to make overly conclusive claims supportable, with an example about structuring, rather than verifying a specific checkable claim. |
| M1-030 | B1 | N/A | N/A | 1 | 1 | medium | The user requests moving the previously generated documents to a named desktop folder, providing one concrete placement constraint. |
| M1-044 | B3 | N/A | 0 | N/A | 0 | high | The user moves from the assistant's layout-success claim to requesting larger fonts without asking for verification of any specific claim. |
| M1-046 | B3 | N/A | N/A | N/A | 0 | medium | After the assistant offered a Markdown outline, the user moves on to request a new Session 14 outline without selecting or checking any substantive claim. |
