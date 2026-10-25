# 22 extra scenarios (11 medium, 11 complex)

Questions are modelled on how rod-lift operators and compliance teams actually slice their data. Expected answers are
computed by `truth.py` straight from the raw files (independent of `copilot/`), and `run.py` checks the agent against them.

## Real-world patterns they come from
- **Failure frequency and "high failed wells"** (two or more failures per well in 12 months), MTBF / run life, repeat failures:
  rod-pump reliability papers, e.g. [Southwestern Petroleum Short Course](https://www.swpshortcourse.org/ppdl/3016) and the
  [Permian Basin sucker-rod failure study](https://ttu-ir.tdl.org/handle/2346/16616) (about 15 months average run time between failures in that data).
- **Downtime as lost production and cost**: [pump downtime and well productivity](https://www.ipa.or.id/en/publications/determination-of-well-productivity-using-pump-downtime-data).
- **Spill reporting deadlines** (24 h written report for about 5 bbl in Colorado): [CPR on Colorado's tougher spill rules](https://www.cpr.org/2013/12/18/oil-and-gas-industry-to-face-tougher-regulations-on-spills) and [state spill-reporting overview](https://ehsdailyadvisor.com/2013/04/states-are-serious-about-oil-spill-reporting).
- **Compliance cadence** (inspection gaps, annual flowline test, 30-day NOV reply, 14-day down report) comes from this challenge's own SOPs (RC-01..05).

I only read search-result summaries of these pages, not the full papers.

## Medium
| ID | Question | Tool |
|---|---|---|
| M1 | High-failed wells (2+ corrective repairs in 12 mo) in Southwest Block 24 | repair_summary |
| M2 | Repair spend by area, 2025, bar chart | repair_summary |
| M3 | Wells that breached the 14-day inspection rule in 2026 (RC-01) | inspection_gaps |
| M4 | Total open fines and which wells carry them | fines |
| M5 | Monthly downtime days, Northeast Block 7, 2026, line | downtime_trend |
| M6 | Mean time between corrective repairs, T200 vs T350 | mtbf |
| M7 | Single most expensive repair in 2026 | top_repairs |
| M8 | Top technicians by corrective repairs in Northeast Block 8 | repair_summary |
| M9 | Recorded status disagreeing with latest inspection, Southwest Block 23 | stale_status |
| M10 | Real spills found by drone vs manual, last 12 months | spill_breakdown |
| M11 | Repairs in progress right now | open_repairs_all |

## Complex
| ID | Question | Tool |
|---|---|---|
| C1 | Wells down more than 14 consecutive days now (RC-03) | consecutive_down |
| C2 | Repeat failures in 2026 (same equipment within 90 days) | repeat_failures |
| C3 | Reportable spills last 12 months: late or unreported, open fines (SR-01) | spill_response_summary |
| C4 | Cost of spill-triggered repairs in 2026 by area | spill_repair_cost |
| C5 | Areas missing the 2026 annual flowline test (RC-02) | flowline_tests |
| C6 | Hot wellheads (>45 °C) that were not producing, 2025, by area | hot_false_alarms |
| C7 | Not producing now and corrective repair in last 90 days | down_with_recent_repair |
| C8 | Wells that just stopped producing at the latest inspection | newly_stopped |
| C9 | 2026 detections removed by corrections vs real spills | correction_impact |
| C10 | Top-5 downtime wells with repair cost and cost per downtime day | downtime_cost |
| C11 | Quarterly trend of reportable spills since 2023 | spill_breakdown |
