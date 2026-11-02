"""Quarter-clustered inference for the backtest.

TSA and CPI-airfare are national signals: every airline gets the same signal in a
given quarter, so airline-quarters are not independent. All tests here treat the
calendar quarter as the unit (effective n = number of quarters).
"""
import json
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
EVAL_START = pd.Timestamp("2023-03-31")
RNG = np.random.default_rng(72)
N_BOOT = 10_000


def ape(res, m):
    return 100 * ((res[m] - res["actual"]) / res["actual"]).abs()


def binom_p(k, n):
    return sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n


def main():
    res = pd.read_csv(P / "backtest_predictions.csv", parse_dates=["end", "asof"])
    ev = res[(res["end"] >= EVAL_START) & ~res["event_excluded"]].dropna(subset=["B2", "M4"]).copy()
    ev["gain"] = ape(ev, "B2") - ape(ev, "M4")           # positive = M4 better
    q = ev.groupby("end").agg(gain=("gain", "mean"), dy=("dy", "mean"), dfare=("dfare", "first"),
                              dx=("dx", "first"), n=("ticker", "count"),
                              b2=("gain", lambda s: ape(ev.loc[s.index], "B2").mean()),
                              m4=("gain", lambda s: ape(ev.loc[s.index], "M4").mean()))
    nq = len(q)

    # 1) Block bootstrap over quarters for the mean APE gain
    boots = np.array([q["gain"].values[RNG.integers(0, nq, nq)].mean() for _ in range(N_BOOT)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    # 2) Quarter-level sign test: does M4 beat B2 in more quarters than chance?
    q_wins = int((q["gain"] > 0).sum())
    # 3) Quarter-level direction: sign of fare acceleration vs sign of avg revenue acceleration
    dd = q[q["dfare"].abs() > 0]
    dir_hits = int((np.sign(dd["dfare"]) == np.sign(dd["dy"])).sum())
    tsa_hits = int((np.sign(q["dx"]) == np.sign(q["dy"])).sum())

    print(f"Quarters evaluated: {nq} ({q.index.min():%Y-%m} .. {q.index.max():%Y-%m})\n")
    print("Per-quarter MAPE (avg across airlines), B2 vs M4:")
    show = q[["n", "dfare", "dy", "b2", "m4", "gain"]].copy()
    show.index = show.index.to_period("Q")
    print(show.round(3).to_string())
    print(f"\nMean APE gain (B2 - M4): {q['gain'].mean():.2f} pts, "
          f"95% quarter-block bootstrap CI [{lo:.2f}, {hi:.2f}]")
    print(f"M4 beats B2 in {q_wins}/{nq} quarters (sign-test p={binom_p(q_wins, nq):.3f})")
    print(f"Fare direction (quarter level): {dir_hits}/{len(dd)} (p={binom_p(dir_hits, len(dd)):.3f})")
    print(f"TSA direction (quarter level):  {tsa_hits}/{nq} (p={binom_p(tsa_hits, nq):.3f})")

    json.dump({"n_quarters": nq, "mean_gain_pts": round(q["gain"].mean(), 3),
               "ci95": [round(lo, 3), round(hi, 3)], "quarter_wins": q_wins,
               "quarter_sign_p": binom_p(q_wins, nq), "fare_dir_hits": dir_hits,
               "fare_dir_n": len(dd), "fare_dir_p": binom_p(dir_hits, len(dd)),
               "tsa_dir_hits": tsa_hits, "tsa_dir_p": binom_p(tsa_hits, nq)},
              open(P / "robustness_summary.json", "w"), indent=2)


if __name__ == "__main__":
    main()
