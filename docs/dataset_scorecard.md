# Dataset Scorecard

How each dataset was evaluated before it was trusted in the model. The criteria mirror
what a buy-side team checks before buying an alternative dataset.

| Criterion | TSA checkpoint volumes | BLS CPI airline fares | SEC XBRL revenue (target) |
|---|---|---|---|
| **What it measures** | People screened at U.S. airport checkpoints, daily | Average change in U.S. airline ticket prices, monthly | Reported total operating revenue per airline |
| **Granularity** | National, daily | National, monthly | Company, quarterly |
| **Entity mapping** | None: not split by airline | None: not split by airline | Direct (CIK → ticker), name checked per file |
| **History used** | 2019-2026 (YoY from 2020) | 2016-2026 | 2018-2026 |
| **Publication lag** | ~1 day | ~2-3 weeks after month end | Median 10 (DAL) to 37 (ALK) days after quarter end |
| **Available at nowcast date** | Full quarter | Months 1-2 of the quarter | Prior quarters only |
| **Point-in-time / revisions** | Archived years revised (Known Crewmembers, late flights); 2026 first print only | NSA series not revised after publication | First-filed value kept; later restatements ignored |
| **Gaps / breaks** | None (2,862 consecutive days) | Oct 2025 not published (shutdown) | 2018 ASC 606 tag change, handled; Q4 derived from 10-K |
| **Panel / coverage bias** | Counts all screened travelers, not airline passengers; first prints excluded Known Crewmember and late-flight counts (per TSA's revision note) | Price index for tickets, not airline revenue per passenger | Total revenue includes cargo, loyalty and other revenue |
| **Correlation with target (2023-2026, quarter level)** | 0.372 | 0.790 | n/a |
| **Correlation with target (2020-2026)** | 0.984 (driven by COVID) | 0.692 | n/a |
| **Direction hit rate (15 quarters)** | 6/15 | 14/15 | n/a |
| **Cost** | Free | Free | Free |
| **Verdict** | Weak alone outside a demand shock | Useful directional signal | Reliable target with care on tag changes and Q4 |

## Sources considered and not used

- **BTS T-100 carrier traffic:** airline-specific, but published with a multi-month lag and
  only through a web form. Not ingested; it is the main next step.
- **A public GitHub repo that nowcasts airline traffic from TSA data:** found during source
  search. Not used, to avoid depending on a third party's processing and undocumented
  provenance; this project pulls every number from the official publisher.
- **Third-party data mirrors (Kaggle, GitHub copies of TSA/SEC data):** rejected for the
  same reason.
