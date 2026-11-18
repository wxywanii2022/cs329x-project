# RQ1 Main 1: local assessor vs human reference

Adjudicated reference: {'N/A': 42, '2': 13, '0': 4, '1': 1}. Agreement over successful pairs; 95% bootstrap intervals (10000 item resamples). Primary run = seed 329.

| Comparison | n | Raw agreement | Cohen's κ | False-missed rate |
|---|---|---|---|---|
| Human A vs B (pre-adjudication) | 59 | 0.780 [0.68, 0.88] | 0.590 [0.40, 0.76] | 0.056 [0.00, 0.12] (3/54) |
| Human A vs adjudicated | 60 | 0.933 [0.87, 0.98] | 0.863 [0.72, 0.97] | 0.036 [0.00, 0.09] (2/56) |
| Human B vs adjudicated | 59 | 0.847 [0.75, 0.93] | 0.702 [0.53, 0.86] | 0.036 [0.00, 0.09] (2/55) |
| qwen35-9b s329 (primary) vs adjudicated | 57 | 0.895 [0.81, 0.96] | 0.753 [0.55, 0.92] | 0.019 [0.00, 0.06] (1/54) |
| qwen35-9b s329 (primary) vs A | 57 | 0.860 [0.77, 0.95] | 0.695 [0.48, 0.87] | 0.019 [0.00, 0.06] (1/53) |
| qwen35-9b s329 (primary) vs B | 56 | 0.839 [0.73, 0.93] | 0.669 [0.47, 0.84] | 0.019 [0.00, 0.06] (1/52) |
| qwen35-9b s330 (seed) vs adjudicated | 56 | 0.911 [0.82, 0.98] | 0.789 [0.59, 0.95] | 0.038 [0.00, 0.10] (2/53) |
| qwen35-9b s330 (seed) vs A | 56 | 0.857 [0.77, 0.95] | 0.688 [0.47, 0.87] | 0.038 [0.00, 0.10] (2/52) |
| qwen35-9b s330 (seed) vs B | 55 | 0.800 [0.69, 0.89] | 0.595 [0.39, 0.78] | 0.039 [0.00, 0.10] (2/51) |
| qwen35-9b s331 (seed) vs adjudicated | 56 | 0.839 [0.73, 0.93] | 0.637 [0.41, 0.83] | 0.058 [0.00, 0.13] (3/52) |
| qwen35-9b s331 (seed) vs A | 56 | 0.786 [0.68, 0.89] | 0.539 [0.31, 0.74] | 0.077 [0.02, 0.16] (4/52) |
| qwen35-9b s331 (seed) vs B | 55 | 0.745 [0.62, 0.85] | 0.495 [0.28, 0.69] | 0.059 [0.00, 0.13] (3/51) |
| qwen38-27b-fp8 s329 (primary) vs adjudicated | 59 | 0.831 [0.73, 0.92] | 0.666 [0.48, 0.83] | 0.036 [0.00, 0.09] (2/55) |
| qwen38-27b-fp8 s329 (primary) vs A | 59 | 0.864 [0.78, 0.95] | 0.745 [0.57, 0.89] | 0.019 [0.00, 0.06] (1/54) |
| qwen38-27b-fp8 s329 (primary) vs B | 58 | 0.793 [0.69, 0.90] | 0.626 [0.44, 0.79] | 0.038 [0.00, 0.10] (2/53) |
| qwen38-27b-fp8 s330 (seed) vs adjudicated | 59 | 0.915 [0.83, 0.98] | 0.826 [0.66, 0.96] | 0.018 [0.00, 0.06] (1/55) |
| qwen38-27b-fp8 s330 (seed) vs A | 59 | 0.949 [0.88, 1.00] | 0.901 [0.77, 1.00] | 0.000 [0.00, 0.00] (0/54) |
| qwen38-27b-fp8 s330 (seed) vs B | 58 | 0.793 [0.69, 0.90] | 0.614 [0.43, 0.78] | 0.038 [0.00, 0.10] (2/53) |
| qwen38-27b-fp8 s331 (seed) vs adjudicated | 59 | 0.831 [0.73, 0.92] | 0.669 [0.48, 0.83] | 0.073 [0.02, 0.15] (4/55) |
| qwen38-27b-fp8 s331 (seed) vs A | 59 | 0.898 [0.81, 0.97] | 0.811 [0.65, 0.94] | 0.037 [0.00, 0.09] (2/54) |
| qwen38-27b-fp8 s331 (seed) vs B | 58 | 0.759 [0.64, 0.86] | 0.567 [0.38, 0.74] | 0.075 [0.02, 0.15] (4/53) |

## qwen35-9b

`Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 1.5 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768; output contract decision-point-v3.

- seed 329: coverage 57/60, failed 3, pending 0, labels {'2': 11, 'N/A': 42, '0': 3, '1': 1}, median output tokens 1020, median latency 22.909 s
  - 1 failed: Evidence quote not in cited turn
  - 1 failed: Context byte budget exceeded
  - 1 failed: A 0 needs evidence quoting the opportunity from an earlier turn
- seed 330: coverage 56/60, failed 4, pending 0, labels {'N/A': 42, '2': 10, '0': 4}, median output tokens 1270.0, median latency 27.531 s
  - 3 failed: Evidence quote not in cited turn
  - 1 failed: Context byte budget exceeded
- seed 331: coverage 56/60, failed 4, pending 0, labels {'N/A': 41, '0': 5, '2': 10}, median output tokens 2539.5, median latency 52.083 s
  - 2 failed: Evidence quote not in cited turn
  - 1 failed: Context byte budget exceeded
  - 1 failed: Missing keys: {'confidence', 'reason', 'unclear_rule', 'evidence', 'behavior', 'label', 'opportunity_status', 'na_reason

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 2 | 1 | 0 | 0 |
| **1** | 0 | 0 | 0 | 1 |
| **2** | 0 | 0 | 10 | 2 |
| **N/A** | 1 | 0 | 1 | 39 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 15 | 0.733 | 0.538 | 0 |
| B2 | 14 | 1.000 | 1.000 | 0 |
| B3 | 14 | 1.000 | 1.000 | 0 |
| B4 | 14 | 0.857 | 0.440 | 1 |

On items where A and B agreed: 43 items, raw 0.977. Where they disagreed: 13 items, raw 0.615.

Seed stability ([329, 330, 331]): 42/52 items unanimous; mean pairwise κ 0.683; unstable: M1-001, M1-002, M1-015, M1-021, M1-026, M1-035, M1-038, M1-042, M1-047, M1-055. Majority-of-seeds vs adjudicated (secondary): raw 0.942, κ 0.863, false-missed 0.020 [0.00, 0.06] (1/49); coverage 52/60 (all seeds valid; ties use primary seed).

High-confidence-zero rule (secondary, valid outputs only): κ 0.753, false-missed 0.019 [0.00, 0.06] (1/54); coverage 57/60.

| v2 false-missed item | Adjudicated | v3 primary outcome |
|---|---|---|
| M1-005 | N/A | N/A |
| M1-027 | N/A | N/A |
| M1-034 | N/A | N/A |
| M1-035 | N/A | N/A |
| M1-040 | N/A | N/A |
| M1-044 | N/A | N/A |

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M1-001 | B1 | N/A | N/A | N/A | 2 | high | User requests delivery of two specific sessions using documented content, establishing format and audience requirements for facilitation. |
| M1-021 | B4 | N/A | N/A | 0 | 0 | high | The user requests the /skills command instead of addressing the visible issue in [FILE_6].docx. |
| M1-031 | B4 | 2 | 2 | N/A | N/A | high | User agreement to implement does not identify or correct a specific problem in an agent output |
| M1-047 | B1 | 2 | 2 | 1 | N/A | high | Requirement to save the conversation as a PDF was explicitly established in Turn 1, and Turn 14 restates it without adding new specifications (N/A). |
| M1-048 | B1 | 1 | 1 | 0 | N/A | medium | User is asking for testing guidance rather than specifying deliverable output requirements with concrete properties |
| M1-055 | B1 | 0 | 1 | 0 | 1 | high | User requests creation of a slideshow without specifying multiple concrete properties like format, length, or audience. |

## qwen38-27b-fp8

`Qwen/Qwen3.8-27B-FP8@017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 0 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768; output contract decision-point-v3.

- seed 329: coverage 59/60, failed 1, pending 0, labels {'N/A': 37, '2': 14, '0': 3, '1': 5}, median output tokens 1484, median latency 55.112 s
  - 1 failed: Context byte budget exceeded
- seed 330: coverage 59/60, failed 1, pending 0, labels {'N/A': 39, '2': 13, '0': 4, '1': 3}, median output tokens 1448, median latency 54.644 s
  - 1 failed: Context byte budget exceeded
- seed 331: coverage 59/60, failed 1, pending 0, labels {'N/A': 37, '2': 12, '0': 6, '1': 4}, median output tokens 1273, median latency 46.610 s
  - 1 failed: Context byte budget exceeded

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 1 | 2 | 0 | 1 |
| **1** | 0 | 1 | 0 | 0 |
| **2** | 0 | 0 | 12 | 1 |
| **N/A** | 2 | 2 | 2 | 35 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 15 | 0.867 | 0.783 | 0 |
| B2 | 15 | 0.667 | 0.286 | 1 |
| B3 | 15 | 0.800 | 0.400 | 1 |
| B4 | 14 | 1.000 | 1.000 | 0 |

On items where A and B agreed: 45 items, raw 0.933. Where they disagreed: 13 items, raw 0.462.

Seed stability ([329, 330, 331]): 51/59 items unanimous; mean pairwise κ 0.820; unstable: M1-005, M1-008, M1-020, M1-026, M1-031, M1-034, M1-035, M1-044. Majority-of-seeds vs adjudicated (secondary): raw 0.847, κ 0.700, false-missed 0.055 [0.00, 0.12] (3/55); coverage 59/60 (all seeds valid; ties use primary seed).

High-confidence-zero rule (secondary, valid outputs only): κ 0.721, false-missed 0.000 [0.00, 0.00] (0/55); coverage 59/60.

| v2 false-missed item | Adjudicated | v3 primary outcome |
|---|---|---|
| M1-005 | N/A | 0 |
| M1-027 | N/A | N/A |
| M1-034 | N/A | 1 |
| M1-035 | N/A | 0 |
| M1-040 | N/A | N/A |
| M1-044 | N/A | N/A |

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M1-005 | B3 | N/A | 0 | N/A | 0 | medium | The user only asks to open the file instead of selecting or checking the agent’s checkable claim about the spreadsheet contents. |
| M1-008 | B2 | N/A | N/A | 2 | 2 | medium | In response to the assistant's request for the missing stock list, the user names a specific file path as the source for the needed stock data. |
| M1-016 | B2 | N/A | 2 | N/A | 2 | medium | The request asks for a specific calculation of FSC space used against available space, which is a usable analysis requirement. |
| M1-020 | B3 | 0 | 0 | 0 | 1 | medium | The user quotes the agent's specific findings numbers back, selecting a particular checkable claim, but makes no request to verify, justify, or recalculate it, leaving the check incomplete. |
| M1-026 | B3 | 0 | 0 | 1 | N/A | medium | The user's turn is a tone-and-phrasing revision request for the SAR narrative rather than a response that selects or checks a substantive claim for verification, justification, or recalculation. |
| M1-030 | B1 | N/A | N/A | 1 | 1 | medium | The turn gives a new deliverable-location constraint with one concrete output property, the destination folder. |
| M1-034 | B2 | N/A | N/A | 1 | 1 | medium | The user specifies the full constituent universe and asks the sub-sector summary to be rebuilt from it, but does not provide a named source or audit trail for the added companies' valuation figures. |
| M1-035 | B2 | N/A | N/A | N/A | 0 | medium | The user requests a comprehensive energy analysis but provides no evidence standard such as sources, calculations, or justification for claims. |
| M1-038 | B2 | 2 | 2 | 2 | N/A | medium | The turn specifies an EBITDA definition and asks for a column-structure design recommendation aligned with the task, which is a design/specification request rather than an output of factual claims or figures needing evidence support. |
| M1-055 | B1 | 0 | 1 | 0 | 1 | high | The opening request asks for a slideshow, giving one concrete format property but no other output requirements. |
