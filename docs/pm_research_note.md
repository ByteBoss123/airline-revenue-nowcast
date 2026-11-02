# Research Note: Public Data Signals for U.S. Airline Revenue

**Coverage:** DAL, UAL, AAL, LUV, ALK, JBLU · **Backtest:** Q1 2023 to Q3 2026 ·
**Signals:** TSA checkpoint volumes, BLS airline-fare CPI

## Bottom line

- **Use the fare CPI for direction, not size.** At quarter end, the change in airline-fare
  inflation called whether airline revenue growth would accelerate or decelerate in
  14 of 15 quarters.
- **Do not use TSA volume as a revenue signal in normal markets.** It called direction in
  6 of 15 quarters, no better than chance. Its strong long-run correlation comes from COVID.
- **Point estimates are not reliably better than a simple carry-forward.** The best model
  cut average error from 5.0% to 3.4%, but won only 7 of 15 quarters, and the improvement is
  not statistically significant.

## Current read (Q3 2026)

Revenue growth has accelerated with fares, not traffic. Delta's Q3 2026 revenue grew 21%
YoY while TSA throughput fell 3% over the same quarter. For airlines whose Q3 2026 revenue
is not yet in this dataset (AAL, ALK), the fare signal is close to zero: airfare inflation
was 21.9% YoY in Jul-Aug vs 21.2% in Apr-May. That points to Q3 growth similar to Q2, a
low-conviction call.

## Where the signal fails

- **Size of the move:** in Q2-Q3 2025 fare swings were much larger than the revenue
  response, and the model overshot.
- **Company-specific events:** national signals cannot see mergers (Alaska-Hawaiian),
  capacity cuts or operational disruptions at one carrier.
- **Data vintage:** historical TSA values were revised after first publication, so the
  backtest is slightly optimistic for TSA.

## Confidence

Moderate on direction, low on magnitude. Effective sample is 15 quarters.

## What would improve it

1. Carrier-level traffic (BTS T-100) to separate one airline from the industry.
2. Comparison with management guidance from earnings releases.
3. First-print TSA vintages, collected going forward, to measure revision bias.
