# RQ1 Main 1: local assessor vs human reference

Adjudicated reference: {'2': 29, 'N/A': 20, '0': 8, '1': 3}. Agreement over successful pairs; 95% bootstrap intervals (10000 item resamples). Primary run = seed 329.

| Comparison | n | Raw agreement | Cohen's κ | False-missed rate |
|---|---|---|---|---|
| Human A vs B (pre-adjudication) | 60 | 0.850 [0.75, 0.93] | 0.772 [0.63, 0.89] | 0.000 [0.00, 0.00] (0/50) |
| Human A vs adjudicated | 60 | 0.950 [0.88, 1.00] | 0.922 [0.82, 1.00] | 0.038 [0.00, 0.10] (2/52) |
| Human B vs adjudicated | 60 | 0.900 [0.82, 0.97] | 0.846 [0.73, 0.95] | 0.000 [0.00, 0.00] (0/52) |
| v2.qwen35-9b s329 (primary) vs adjudicated | 57 | 0.754 [0.63, 0.86] | 0.626 [0.46, 0.78] | 0.100 [0.02, 0.19] (5/50) |
| v2.qwen35-9b s329 (primary) vs A | 57 | 0.719 [0.60, 0.82] | 0.574 [0.39, 0.73] | 0.104 [0.02, 0.20] (5/48) |
| v2.qwen35-9b s329 (primary) vs B | 57 | 0.702 [0.58, 0.81] | 0.555 [0.38, 0.71] | 0.113 [0.04, 0.20] (6/53) |
| v2.qwen35-9b s330 (seed) vs adjudicated | 52 | 0.673 [0.54, 0.79] | 0.515 [0.34, 0.69] | 0.156 [0.06, 0.27] (7/45) |
| v2.qwen35-9b s330 (seed) vs A | 52 | 0.712 [0.58, 0.83] | 0.571 [0.39, 0.74] | 0.116 [0.03, 0.22] (5/43) |
| v2.qwen35-9b s330 (seed) vs B | 52 | 0.673 [0.54, 0.79] | 0.520 [0.35, 0.69] | 0.170 [0.07, 0.28] (8/47) |
| v2.qwen35-9b s331 (seed) vs adjudicated | 55 | 0.673 [0.55, 0.80] | 0.496 [0.32, 0.67] | 0.104 [0.02, 0.20] (5/48) |
| v2.qwen35-9b s331 (seed) vs A | 55 | 0.691 [0.56, 0.82] | 0.526 [0.35, 0.70] | 0.087 [0.02, 0.18] (4/46) |
| v2.qwen35-9b s331 (seed) vs B | 55 | 0.673 [0.55, 0.80] | 0.504 [0.33, 0.67] | 0.098 [0.02, 0.19] (5/51) |
| v2.qwen38-27b-fp8 s329 (primary) vs adjudicated | 60 | 0.917 [0.83, 0.98] | 0.868 [0.75, 0.97] | 0.038 [0.00, 0.10] (2/52) |
| v2.qwen38-27b-fp8 s329 (primary) vs A | 60 | 0.917 [0.83, 0.98] | 0.868 [0.75, 0.97] | 0.040 [0.00, 0.10] (2/50) |
| v2.qwen38-27b-fp8 s329 (primary) vs B | 60 | 0.850 [0.75, 0.93] | 0.770 [0.63, 0.89] | 0.073 [0.02, 0.15] (4/55) |
| v2.qwen38-27b-fp8 s330 (seed) vs adjudicated | 60 | 0.883 [0.80, 0.95] | 0.818 [0.68, 0.93] | 0.038 [0.00, 0.10] (2/52) |
| v2.qwen38-27b-fp8 s330 (seed) vs A | 60 | 0.867 [0.78, 0.95] | 0.792 [0.65, 0.92] | 0.020 [0.00, 0.06] (1/50) |
| v2.qwen38-27b-fp8 s330 (seed) vs B | 60 | 0.833 [0.73, 0.92] | 0.746 [0.60, 0.88] | 0.055 [0.00, 0.12] (3/55) |
| v2.qwen38-27b-fp8 s331 (seed) vs adjudicated | 60 | 0.900 [0.82, 0.97] | 0.846 [0.72, 0.95] | 0.038 [0.00, 0.10] (2/52) |
| v2.qwen38-27b-fp8 s331 (seed) vs A | 60 | 0.850 [0.75, 0.93] | 0.769 [0.63, 0.90] | 0.040 [0.00, 0.10] (2/50) |
| v2.qwen38-27b-fp8 s331 (seed) vs B | 60 | 0.833 [0.73, 0.92] | 0.749 [0.61, 0.88] | 0.073 [0.02, 0.15] (4/55) |
| v3.qwen35-9b s329 (primary) vs adjudicated | 58 | 0.724 [0.60, 0.83] | 0.575 [0.42, 0.73] | 0.020 [0.00, 0.06] (1/50) |
| v3.qwen35-9b s329 (primary) vs A | 58 | 0.741 [0.62, 0.84] | 0.603 [0.44, 0.76] | 0.000 [0.00, 0.00] (0/48) |
| v3.qwen35-9b s329 (primary) vs B | 58 | 0.655 [0.53, 0.78] | 0.471 [0.31, 0.64] | 0.057 [0.00, 0.13] (3/53) |
| v3.qwen35-9b s330 (seed) vs adjudicated | 56 | 0.732 [0.61, 0.84] | 0.589 [0.41, 0.75] | 0.020 [0.00, 0.06] (1/49) |
| v3.qwen35-9b s330 (seed) vs A | 56 | 0.732 [0.61, 0.84] | 0.594 [0.43, 0.75] | 0.021 [0.00, 0.07] (1/47) |
| v3.qwen35-9b s330 (seed) vs B | 56 | 0.661 [0.54, 0.79] | 0.477 [0.30, 0.65] | 0.059 [0.00, 0.13] (3/51) |
| v3.qwen35-9b s331 (seed) vs adjudicated | 50 | 0.740 [0.62, 0.86] | 0.585 [0.40, 0.76] | 0.045 [0.00, 0.12] (2/44) |
| v3.qwen35-9b s331 (seed) vs A | 50 | 0.740 [0.62, 0.86] | 0.591 [0.42, 0.76] | 0.047 [0.00, 0.12] (2/43) |
| v3.qwen35-9b s331 (seed) vs B | 50 | 0.700 [0.56, 0.82] | 0.526 [0.34, 0.70] | 0.064 [0.00, 0.15] (3/47) |
| v3.qwen38-27b-fp8 s329 (primary) vs adjudicated | 60 | 0.867 [0.78, 0.95] | 0.794 [0.65, 0.92] | 0.058 [0.00, 0.13] (3/52) |
| v3.qwen38-27b-fp8 s329 (primary) vs A | 60 | 0.867 [0.77, 0.95] | 0.794 [0.65, 0.92] | 0.040 [0.00, 0.10] (2/50) |
| v3.qwen38-27b-fp8 s329 (primary) vs B | 60 | 0.817 [0.72, 0.92] | 0.722 [0.57, 0.86] | 0.073 [0.02, 0.15] (4/55) |
| v3.qwen38-27b-fp8 s330 (seed) vs adjudicated | 60 | 0.933 [0.87, 0.98] | 0.896 [0.79, 0.97] | 0.019 [0.00, 0.06] (1/52) |
| v3.qwen38-27b-fp8 s330 (seed) vs A | 60 | 0.883 [0.80, 0.95] | 0.818 [0.69, 0.93] | 0.020 [0.00, 0.06] (1/50) |
| v3.qwen38-27b-fp8 s330 (seed) vs B | 60 | 0.883 [0.80, 0.95] | 0.821 [0.69, 0.93] | 0.036 [0.00, 0.09] (2/55) |
| v3.qwen38-27b-fp8 s331 (seed) vs adjudicated | 59 | 0.864 [0.78, 0.95] | 0.795 [0.66, 0.92] | 0.039 [0.00, 0.10] (2/51) |
| v3.qwen38-27b-fp8 s331 (seed) vs A | 59 | 0.831 [0.73, 0.92] | 0.744 [0.60, 0.87] | 0.041 [0.00, 0.10] (2/49) |
| v3.qwen38-27b-fp8 s331 (seed) vs B | 59 | 0.864 [0.76, 0.95] | 0.798 [0.66, 0.92] | 0.056 [0.00, 0.12] (3/54) |

## v2.qwen35-9b

`Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 1.5 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768; output contract decision-point-v2.

- seed 329: coverage 57/60, failed 3, pending 0, labels {'2': 22, 'N/A': 22, '0': 10, '1': 3}, median output tokens 3362, median latency 72.119 s
  - post-hoc (not pre-declared), also scoring the 3 outputs that failed only the exact-quote check: n 60, raw 0.767 [0.65, 0.87], κ 0.645 [0.48, 0.79], false-missed 0.096 [0.02, 0.18]
  - 3 failed: Evidence quote not in cited turn
- seed 330: coverage 52/60, failed 8, pending 0, labels {'2': 18, '0': 12, 'N/A': 20, '1': 2}, median output tokens 3846.0, median latency 82.219 s
  - post-hoc (not pre-declared), also scoring the 8 outputs that failed only the exact-quote check: n 60, raw 0.667 [0.55, 0.78], κ 0.496 [0.33, 0.66], false-missed 0.135 [0.04, 0.24]
  - 8 failed: Evidence quote not in cited turn
- seed 331: coverage 55/60, failed 5, pending 0, labels {'0': 8, 'N/A': 24, '2': 21, '1': 2}, median output tokens 3305, median latency 70.404 s
  - post-hoc (not pre-declared), also scoring the 4 outputs that failed only the exact-quote check: n 59, raw 0.695 [0.58, 0.81], κ 0.532 [0.35, 0.70], false-missed 0.098 [0.02, 0.19]
  - 4 failed: Evidence quote not in cited turn
  - 1 failed: Missing keys: {'confidence', 'reason', 'unclear_rule', 'opportunity_status', 'behavior', 'na_reason', 'evidence', 'label

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 5 | 0 | 1 | 1 |
| **1** | 0 | 1 | 0 | 2 |
| **2** | 2 | 1 | 21 | 3 |
| **N/A** | 3 | 1 | 0 | 16 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 14 | 1.000 | 1.000 | 0 |
| B2 | 14 | 0.643 | 0.421 | 2 |
| B3 | 14 | 0.571 | 0.368 | 2 |
| B4 | 15 | 0.800 | 0.628 | 1 |

On items where A and B agreed: 48 items, raw 0.792. Where they disagreed: 9 items, raw 0.556.

Seed stability ([329, 330, 331]): 28/48 items unanimous; mean pairwise κ 0.535; unstable: M2-002, M2-004, M2-019, M2-022, M2-027, M2-028, M2-029, M2-031, M2-033, M2-034, M2-036, M2-038, M2-039, M2-042, M2-045, M2-046, M2-049, M2-051, M2-053, M2-059. Majority-of-seeds vs adjudicated (secondary): raw 0.750, κ 0.625, false-missed 0.116 [0.02, 0.22] (5/43); coverage 48/60 (all seeds valid; ties use primary seed).

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M2-004 | B4 | N/A | N/A | N/A | 0 | high | User confirms network settings update but does not identify a specific problem in the agent's output or request a correction. |
| M2-016 | B2 | N/A | N/A | N/A | 0 | high | The user requests an analytical presentation on benefits and savings but provides no specific requirements for supporting evidence or sources. |
| M2-018 | B2 | 2 | 2 | 2 | N/A | high | sources are supplied in the task instructions with no requirement for the output to cite evidence or detail the calculation method. |
| M2-027 | B4 | N/A | N/A | N/A | 1 | medium | User requests verification of calculations but does not identify a specific error or provide clear correction guidance. |
| M2-033 | B3 | 0 | 0 | N/A | 2 | medium | The user specifically challenges the agent's reported font typeface and requests a precise replacement, treating the formatting claim as a verifiable property. |
| M2-035 | B4 | 2 | 2 | 1 | N/A | high | User repeats original task instructions without identifying a problem in prior output |
| M2-039 | B3 | 1 | 0 | 1 | N/A | high | The user issued new quality criteria for revision rather than selecting a prior agent claim to verify. |
| M2-042 | B2 | 2 | 2 | 2 | 1 | high | Turn requests specific calculations without requiring citation, source attribution, or evidence trail for the numerical results. |
| M2-045 | B3 | 2 | 2 | 2 | 0 | high | User accepts the output without verifying or checking substantive claims; instead flags errors which is B4 behavior. |
| M2-046 | B2 | 1 | 1 | 1 | N/A | high | User request asks agent to produce output but doesn't specify how the agent should obtain the underlying data or verify claims within that output. |
| M2-047 | B3 | 0 | 0 | 1 | N/A | medium | Turn is task specification/instruction turn, not a response to an agent output containing substantive claims to verify |
| M2-049 | B2 | 2 | 2 | 2 | 0 | high | The turn requests a payroll spreadsheet based on CBA guidelines but does not specify evidence requirements, citation standards, or verification methods for any claims in the output. |
| M2-052 | B3 | N/A | N/A | N/A | 0 | high | The user accepts the agent's factual claim about the file listing and proceeds without verifying or challenging the information. |
| M2-053 | B3 | 2 | 2 | 2 | N/A | high | No visible substantive claim from agent regarding inclusion of 'Additional Talks' to verify. |

## v2.qwen38-27b-fp8

`Qwen/Qwen3.8-27B-FP8@017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 0 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768; output contract decision-point-v2.

- seed 329: coverage 60/60, failed 0, pending 0, labels {'2': 30, 'N/A': 19, '0': 9, '1': 2}, median output tokens 1542.0, median latency 58.150 s
- seed 330: coverage 60/60, failed 0, pending 0, labels {'2': 29, '0': 8, 'N/A': 19, '1': 4}, median output tokens 1831.0, median latency 71.845 s
- seed 331: coverage 60/60, failed 0, pending 0, labels {'2': 29, 'N/A': 17, '0': 9, '1': 5}, median output tokens 1600.0, median latency 63.965 s

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 7 | 0 | 0 | 1 |
| **1** | 0 | 2 | 0 | 1 |
| **2** | 0 | 0 | 29 | 0 |
| **N/A** | 2 | 0 | 1 | 17 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 15 | 1.000 | 1.000 | 0 |
| B2 | 15 | 0.867 | 0.717 | 1 |
| B3 | 15 | 0.867 | 0.792 | 1 |
| B4 | 15 | 0.933 | 0.848 | 0 |

On items where A and B agreed: 51 items, raw 0.961. Where they disagreed: 9 items, raw 0.667.

Seed stability ([329, 330, 331]): 52/60 items unanimous; mean pairwise κ 0.853; unstable: M2-002, M2-009, M2-016, M2-019, M2-039, M2-047, M2-053, M2-057. Majority-of-seeds vs adjudicated (secondary): raw 0.917, κ 0.870, false-missed 0.038 [0.00, 0.10] (2/52); coverage 60/60 (all seeds valid; ties use primary seed).

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M2-016 | B2 | N/A | N/A | N/A | 0 | medium | The turn requests a benefits presentation but gives no source, data, or justification requirement. |
| M2-031 | B4 | 0 | 0 | N/A | N/A | medium | The target turn only confirms the identified transaction and does not address an established problem in the agent's output. |
| M2-039 | B3 | 1 | 0 | 1 | N/A | medium | The turn states new quality criteria for the test questions rather than selecting a specific checkable claim from the agent's prior output for verification. |
| M2-052 | B3 | N/A | N/A | N/A | 0 | high | The prior file-count claim was checkable, but the target only accepts it and sets a future working location rather than requesting verification. |
| M2-057 | B2 | N/A | 2 | N/A | 2 | medium | The turn requests a specific calculation of revenue recognized from long-term contracts for each of the three years. |

## v3.qwen35-9b

`Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 1.5 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768; output contract decision-point-v3.

- seed 329: coverage 58/60, failed 2, pending 0, labels {'2': 19, '0': 6, 'N/A': 32, '1': 1}, median output tokens 2175.0, median latency 46.854 s
  - 2 failed: Evidence quote not in cited turn
- seed 330: coverage 56/60, failed 4, pending 0, labels {'N/A': 31, '2': 17, '0': 5, '1': 3}, median output tokens 4561.0, median latency 97.443 s
  - 4 failed: Evidence quote not in cited turn
- seed 331: coverage 50/60, failed 10, pending 0, labels {'2': 18, 'N/A': 26, '0': 5, '1': 1}, median output tokens 3597.0, median latency 76.855 s
  - 9 failed: Evidence quote not in cited turn
  - 1 failed: A 0 needs evidence quoting the opportunity from an earlier turn

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 5 | 0 | 0 | 3 |
| **1** | 0 | 0 | 0 | 3 |
| **2** | 1 | 1 | 19 | 8 |
| **N/A** | 0 | 0 | 0 | 18 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 15 | 0.933 | 0.837 | 0 |
| B2 | 14 | 0.500 | 0.234 | 0 |
| B3 | 14 | 0.571 | 0.396 | 1 |
| B4 | 15 | 0.867 | 0.688 | 0 |

On items where A and B agreed: 50 items, raw 0.760. Where they disagreed: 8 items, raw 0.500.

Seed stability ([329, 330, 331]): 29/46 items unanimous; mean pairwise κ 0.574; unstable: M2-002, M2-006, M2-007, M2-014, M2-016, M2-018, M2-021, M2-028, M2-033, M2-034, M2-035, M2-036, M2-038, M2-042, M2-045, M2-046, M2-050. Majority-of-seeds vs adjudicated (secondary): raw 0.783, κ 0.653, false-missed 0.000 [0.00, 0.00] (0/41); coverage 46/60 (all seeds valid; ties use primary seed).

High-confidence-zero rule (secondary, valid outputs only): κ 0.575, false-missed 0.020 [0.00, 0.06] (1/50); coverage 58/60.

| v2 false-missed item | Adjudicated | v3 primary outcome |
|---|---|---|

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M2-002 | B3 | 2 | 0 | 2 | 0 | high | User identifies a content defect in the agent's output rather than selecting an agent claim to check or ask for verification. |
| M2-006 | B4 | 2 | 2 | 2 | N/A | high | The user requests corrections but specific content errors are not visible in prior turns, preventing citation of a pre-existing problem as required. |
| M2-007 | B3 | 0 | 0 | 0 | N/A | high | User says share (delivery request), not selecting a substantive claim to verify |
| M2-014 | B2 | 2 | 2 | 2 | 1 | high | User requests factual data gathering and analysis but does not specify particular sources, verification methods, or citation requirements for the claims. |
| M2-028 | B2 | 2 | 2 | 2 | N/A | high | This is a computation/recalculation task based on internal assumptions, not a request requiring external evidence or source support. |
| M2-029 | B2 | 2 | 2 | 2 | N/A | high | Task requests use of provided reference files but does not specify any evidence support standard for the required output. |
| M2-034 | B1 | 1 | 1 | 1 | N/A | high | The user requests delivery of existing content without establishing new deliverable requirements; the original task specifications in turn 1 fully define the output. |
| M2-035 | B4 | 2 | 2 | 1 | N/A | high | User is restating requirements from turn 3 without adding new specifications; the assistant has not yet produced an output problem that requires correction at turn 147. |
| M2-036 | B2 | 2 | 2 | 2 | N/A | high | The user asks for calculations but does not require the output to include evidence, citations, or work display; the data source was already supplied by the tool. |
| M2-039 | B3 | 1 | 0 | 1 | N/A | high | No visible agent output before turn 16 contains specific test questions requiring verification; turn 16 provides new specifications rather than checking existing claims. |
| M2-042 | B2 | 2 | 2 | 2 | N/A | medium | No prior agent output contains factual claims requiring evidence support to verify; turn 24 itself is a new task request, not a response to agent-generated claims. |
| M2-046 | B2 | 1 | 1 | 1 | N/A | high | user requests report with reasoned arguments but does not specify evidence types, sources, or verification standards required for the claims |
| M2-047 | B3 | 0 | 0 | 1 | N/A | high | Turn 244 restates task instructions without selecting or checking a substantive claim from an earlier agent output. |
| M2-049 | B2 | 2 | 2 | 2 | N/A | high | The task requests building a spreadsheet tool rather than making factual claims needing evidentiary support. |
| M2-053 | B3 | 2 | 2 | 2 | N/A | high | Cannot judge B3 because I cannot verify any claim against the 'Additional Talks' list from available context; the user is checking completion but I cannot see the source material. |
| M2-059 | B3 | 0 | 0 | 0 | N/A | high | User provides new task instruction following file delivery and progress update, which precludes verification behavior per section 16. |

## v3.qwen38-27b-fp8

`Qwen/Qwen3.8-27B-FP8@017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`; temperature 1.0; command flags `--thinking on --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 0 --repetition-penalty 1.0 --http-timeout 3300`; max output tokens 32768; output contract decision-point-v3.

- seed 329: coverage 60/60, failed 0, pending 0, labels {'N/A': 22, '2': 26, '0': 9, '1': 3}, median output tokens 1961.5, median latency 79.904 s
- seed 330: coverage 60/60, failed 0, pending 0, labels {'2': 28, 'N/A': 21, '0': 7, '1': 4}, median output tokens 1701.5, median latency 63.201 s
- seed 331: coverage 59/60, failed 1, pending 0, labels {'2': 25, '1': 6, 'N/A': 20, '0': 8}, median output tokens 1875, median latency 74.281 s
  - 1 failed: Evidence quote not in cited turn

Primary confusion (rows = adjudicated, columns = model):

| | 0 | 1 | 2 | N/A |
|---|---|---|---|---|
| **0** | 6 | 0 | 0 | 2 |
| **1** | 1 | 2 | 0 | 0 |
| **2** | 0 | 1 | 26 | 2 |
| **N/A** | 2 | 0 | 0 | 18 |

| Behavior | n | Raw | κ | False-missed count |
|---|---|---|---|---|
| B1 | 15 | 1.000 | 1.000 | 0 |
| B2 | 15 | 0.867 | 0.746 | 1 |
| B3 | 15 | 0.667 | 0.493 | 2 |
| B4 | 15 | 0.933 | 0.848 | 0 |

On items where A and B agreed: 51 items, raw 0.922. Where they disagreed: 9 items, raw 0.556.

Seed stability ([329, 330, 331]): 52/59 items unanimous; mean pairwise κ 0.872; unstable: M2-001, M2-002, M2-009, M2-016, M2-035, M2-038, M2-039. Majority-of-seeds vs adjudicated (secondary): raw 0.915, κ 0.869, false-missed 0.020 [0.00, 0.06] (1/51); coverage 59/60 (all seeds valid; ties use primary seed).

High-confidence-zero rule (secondary, valid outputs only): κ 0.790, false-missed 0.019 [0.00, 0.06] (1/52); coverage 60/60.

| v2 false-missed item | Adjudicated | v3 primary outcome |
|---|---|---|

| Item | Behavior | Adjudicated | A | B | Model | Confidence | Model reason |
|---|---|---|---|---|---|---|---|
| M2-001 | B2 | 2 | 2 | 2 | N/A | medium | The user supplies the source documents and constrains the article to them, with instructions focused on narrative structure and style rather than an evidence-verification or citation methodology. |
| M2-002 | B3 | 2 | 0 | 2 | N/A | medium | The user is reporting a possible missing column and asking about its impact, not selecting or requesting verification of a specific substantive claim made by the agent. |
| M2-016 | B2 | N/A | N/A | N/A | 0 | medium | The request seeks a board presentation making benefit and fund-saving claims, but it gives no usable source, data, citation, or calculation requirement. |
| M2-031 | B4 | 0 | 0 | N/A | N/A | medium | The preceding agent output is a confirmation question about a transaction, and no specific problem in that output is established as needing correction. |
| M2-039 | B3 | 1 | 0 | 1 | 0 | medium | The agent's summary made checkable regulatory claims (e.g., the 11 U.S.C. § 362 automatic-stay reference), but the user moved on to a new requirement without selecting any claim to verify. |
| M2-047 | B3 | 0 | 0 | 1 | N/A | high | The target user turn only restates the task instructions and does not respond to or select any checkable claim from the preceding agent output. |
| M2-052 | B3 | N/A | N/A | N/A | 0 | high | The user accepts the assistant's checkable file-list claim and moves on without asking for verification. |
| M2-053 | B3 | 2 | 2 | 2 | 1 | medium | The user asks for verification of a broad category rather than identifying one specific claim to check. |
