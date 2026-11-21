# RQ1 Main 2 — held-out results (60 items, adjudicated reference)

All 4 jobs COMPLETED 2026-11-21 00:53–01:05 PST; no preemption, no resume. Full tables:
`report_via_rq1_report.md` (unmodified scripts/rq1_report.py run through a symlinked tree
main60-sX -> main2-sX, so its title still says "Main 1") and `extra_metrics.json`
(scripts/main2_extra_metrics.py).

| Comparison (vs adjudicated) | Coverage | Raw [95% CI] | κ [95% CI] | FMR | Ref-0 detected |
|---|---|---|---|---|---|
| Human A | 60/60 | 0.950 [0.88, 1.00] | 0.922 [0.82, 1.00] | 2/52 | – |
| Human B | 60/60 | 0.900 [0.82, 0.97] | 0.846 [0.73, 0.95] | 0/52 | – |
| **v3 27B s329 (primary)** | 60/60 | 0.867 [0.78, 0.95] | 0.794 [0.65, 0.92] | 3/52 | 6/8 |
| v2 27B s329 (comparator) | 60/60 | 0.917 [0.83, 0.98] | 0.868 [0.75, 0.97] | 2/52 | 7/8 |
| v3 27B majority (b) | 59/60 | 0.915 | 0.869 | 1/51 | |
| v2 27B majority | 60/60 | 0.917 | 0.870 | 2/52 | |
| v3 27B high-conf-zero (c) | 60/60 | | 0.790 | 1/52 | |
| v3 9B s329 | 58/60 | 0.724 | 0.575 | 1/50 | 5/8 |
| v2 9B s329 | 57/60 | 0.754 | 0.626 | 5/50 | 5/8 |

Paired, same items (27B): s329 v2 better (4 items only v2 right vs 1 only v3); s330 v3 better
(κ 0.896 vs 0.818, 3 vs 0); s331 v2 slightly better (κ 0.844 vs 0.795). Seed stability 27B:
v3 52/59 unanimous (κ 0.872), v2 52/60 (κ 0.853). 9B: v3 cuts FMR (5/50 -> 1/50, 7/43 -> 0/43
on s330) but has 2–10 quote failures per seed and κ 0.50–0.63 for both contracts.

Reading (per prereg: FMR with coverage and zero detection; no automatic RQ2 switch):
- The pre-declared primary comparison does NOT show v3 improving on v2 on held-out data;
  differences are within bootstrap noise and flip sign across seeds.
- v3's misses lean toward over-applying the opportunity gate (N/A where humans saw an
  opportunity: M2-001, M2-002, M2-047).
- 27B (either contract) agrees with the adjudicated reference at roughly human-B level.
- Caveats: 51/60 adjudicated labels are A/B-agreed (not independent of A/B); item bootstrap
  ignores participant clustering; sample is opportunity-enriched, session- not participant-held-out.
