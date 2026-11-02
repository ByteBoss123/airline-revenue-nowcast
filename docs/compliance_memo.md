# Data Compliance Memo

Scope: the three datasets used in this project. Prepared as a pre-use review of the kind a
research team runs with Compliance before a dataset enters an investment process.

## Summary

| Question | TSA | BLS CPI | SEC EDGAR |
|---|---|---|---|
| Publisher | U.S. Transportation Security Administration | U.S. Bureau of Labor Statistics | U.S. Securities and Exchange Commission |
| How obtained | Copied by hand from the public page tsa.gov/travel/passenger-volumes | Downloaded by hand from data.bls.gov | Saved by hand from data.sec.gov company-facts JSON |
| Contains personal data (PII)? | No: daily national totals | No: price index | No: company financial statements |
| Could be MNPI? | No: published to everyone at the same time | No: scheduled public release | No: public filings |
| Terms-of-use risk | Low: U.S. federal government data | Low: U.S. federal government data | Low: public filings; automated access must follow SEC fair-access rules |
| Scraping involved? | No automated scraping | No | No automated scraping in this repo |
| Provenance recorded? | Yes: file SHA-256, source URL, ingest time | Yes | Yes, plus CIK and entity-name check |

## Material non-public information (MNPI)

The project never uses information before it was public:
- Revenue enters a training set only after its SEC filing date.
- The fare CPI is used only after its publication date; month 3 of the current quarter is
  excluded at the nowcast date.
- TSA is used through the last complete day of the quarter, all published by the nowcast date.

These rules are enforced by tests in `tests/test_point_in_time.py`.

**Disclosed exception:** archived TSA figures were revised by TSA after first publication.
The revised values were public when downloaded but were not all public at each historical
nowcast date. This is a backtest-accuracy issue, not an MNPI issue: no non-public source is
involved.

## Personal data

None of the datasets contain individual-level records. No PII screening or masking was
required.

## Terms of use and access

- TSA and BLS publish these series openly as U.S. federal government data.
- The SEC asks automated users to identify themselves (declared User-Agent with contact
  email) and to keep request rates within its fair-access limits. The optional
  `fetch_data.py` script sends a declared User-Agent and makes one request per file.

## Questions this project would ask a commercial data vendor

1. How is the panel sourced, and do the people in it consent to that use?
2. Is any data derived from an employee, contractor or company that owes the subject a
   duty of confidentiality?
3. Is PII removed before delivery, and how is re-identification risk tested?
4. Are historical values point-in-time (as first delivered) or backfilled and revised?
5. Has the panel's coverage or methodology changed, and on what dates?
6. Do the vendor's own terms with its data sources permit resale for investment use?

These are the issues behind the SEC's 2021 enforcement action against the app-analytics
vendor App Annie, which was charged with misrepresenting how it built the data it sold to
investment firms.
