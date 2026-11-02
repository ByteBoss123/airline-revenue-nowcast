# Alternative Data Cheat Sheet (interview prep)

One page on how buy-side research teams use alternative data. Vendor names are common
examples of each category, not endorsements; check current ownership and products before
naming one in an interview.

## Main data categories

| Category | What it measures | Typical use | Example vendors | Key pitfalls |
|---|---|---|---|---|
| **Card transactions** | Spending from a panel of debit/credit cards or bank accounts | Nowcast consumer company revenue before earnings | Bloomberg Second Measure, Earnest Analytics, Facteus | Panel bias (demographics, region), merchant mapping errors, panel churn |
| **Email receipts** | Itemized purchases parsed from opted-in inboxes | Order counts, basket size, e-commerce share | Rakuten Intelligence, YipitData | Consent and PII handling, small panels for niche brands |
| **Web traffic** | Visits and engagement on company websites | Demand for online businesses, share shifts | Similarweb | Bots, measurement method changes, visits ≠ purchases |
| **App data** | Downloads, active users, in-app revenue estimates | Mobile-first companies, games, subscriptions | Sensor Tower, data.ai (formerly App Annie) | Estimates, not observed counts; SDK/consent sourcing risk |
| **Foot traffic / geolocation** | Visits to physical stores from phone location data | Retail, restaurants, real estate | Placer.ai, Advan | Location consent, store-boundary errors, sample drift |
| **Job postings** | Open roles by company, title, location | Hiring plans, expansion, cost pressure | LinkUp, Revelio Labs, Thinknum | Reposted/duplicate ads, postings ≠ hires |
| **Web-scraped prices / product data** | Prices, stock levels, product listings | Pricing power, inflation, promotions | Thinknum, in-house scraping | Site terms of use, blocking, layout changes break scrapers |
| **Satellite / shipping** | Parking lots, oil storage, vessel movements | Commodities, retail traffic, supply chains | Orbital Insight, Spire, MarineTraffic | Cloud cover, cost, long processing lag |
| **Government / public** | TSA screenings, BLS prices, BTS traffic, Census retail | Industry-level demand and price signals | Free (agencies) | National not company-level, revisions, publication delays |

## How a dataset is evaluated before buying (trial process)

1. **Coverage:** which companies/tickers does it map to, and how much of each company's
   business does it see?
2. **History:** enough years to cover at least one cycle and several earnings seasons.
3. **Point-in-time:** are historical values as first delivered, or backfilled/revised?
   Backfilled data inflates backtests.
4. **Lag:** how soon after the period does it arrive vs the company's report date?
5. **Panel stability:** has panel size or method changed? A changing panel creates fake trends.
6. **Signal test:** correlation with reported KPIs, direction hit rate, and error vs a naive
   baseline, out of sample, with clustered statistics.
7. **Compliance review:** sourcing, consent, PII, MNPI and terms of use (below).
8. **Cost vs value:** does the signal add to what the team already has?

## Compliance questions (the ones Compliance teams ask)

- **MNPI:** could the data come from someone who owes a duty of confidentiality, e.g. an
  employee, contractor or company insider? If yes, stop.
- **Consent and PII:** did the people in the panel agree to this use? Is PII removed and is
  re-identification risk tested?
- **Terms of use:** do the source website's terms allow scraping and commercial use? Does
  the vendor have the right to resell to investment firms?
- **Representations:** does the vendor's description of its sourcing match what it
  actually does?

**Case to know:** in 2021 the SEC charged app-analytics firm App Annie and its co-founder
with misrepresenting to trading firms how its estimates were made, while using
confidential company data. It is the standard example of why vendor sourcing claims are
diligenced, not trusted.

## Point72 Market Intelligence context (from the job posting)

- Research products are built "compliant" with the Compliance team involved, so expect
  questions on sourcing and MNPI, not just modeling.
- The role covers methodology choice, data collection and quality, modeling and
  performance monitoring end to end.

## How to talk about the airline project

- **Point-in-time discipline:** first-filed revenue values, publication-date rules for CPI,
  tests that fail on look-ahead.
- **The COVID trap:** TSA correlates 0.98 with revenue over 2020-2026 but 0.37 in normal
  years. A long-run correlation can be one regime.
- **Honest inference:** airline-quarters share one national signal per quarter, so the
  tests treat 15 quarters as the sample, not 84.
- **Price vs volume:** 2026 revenue growth came from fares; volume pointed the wrong way.
