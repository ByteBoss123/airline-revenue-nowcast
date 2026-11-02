"""Point-in-time walk-forward backtest: nowcast airline quarterly revenue.

Nowcast for quarter q is made the day after the quarter ends (TSA data for the
full quarter is public; the company has not reported yet).
  target  y = log(Rev_q / Rev_{q-4})          revenue YoY growth
  signal  x = log(TSA_q / TSA_{q-4})          checkpoint-volume YoY growth

Point-in-time rule: when nowcasting q, a model may only train on quarters whose
revenue was FILED before the nowcast date. Revenue bases (Rev_{q-4}) must also be
filed before that date (always true in this data; asserted).

Models
  B1 seasonal naive      Rev_q = Rev_{q-4}
  B2 last-reported YoY   y_q = y of the latest quarter filed before the as-of date
  M1 TSA regression      y = a + b*x, pooled across airlines, expanding window
  M2 TSA + carry         y = a + b*x + c*y_last  (y_last as in B2)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
EVAL_START = pd.Timestamp("2023-03-31")      # post-COVID-normalization evaluation window
MIN_TRAIN = 12                               # minimum airline-quarters before fitting
# Alaska acquired Hawaiian Airlines (closed Sep 2024): YoY growth through Q3 2025
# reflects the merger, not demand. Reported separately, excluded from headline.
EVENT_EXCLUDE = {("ALK", q) for q in pd.date_range("2024-12-31", "2025-09-30", freq="QE")}


def load():
    t = pd.read_csv(P / "tsa_daily.csv", parse_dates=["date"])
    t["end"] = t["date"].dt.to_period("Q").dt.end_time.dt.normalize()
    tsa = t.groupby("end")["travelers"].agg(["sum", "count"])
    full = tsa[tsa["count"] >= 89]["sum"]                 # complete quarters only
    tsa_yoy = np.log(full / full.shift(4)).dropna().rename("x")

    r = pd.read_csv(P / "sec_quarterly_revenue.csv", parse_dates=["end", "filed"])
    r = r.sort_values(["ticker", "end"])
    r["rev_lag4"] = r.groupby("ticker")["val"].shift(4)
    r["filed_lag4"] = r.groupby("ticker")["filed"].shift(4)
    r["end_lag4"] = r.groupby("ticker")["end"].shift(4)
    r = r[(r["end_lag4"] == r["end"] - pd.offsets.QuarterEnd(4))]  # true year-ago quarter
    r["y"] = np.log(r["val"] / r["rev_lag4"])
    df = r.merge(tsa_yoy, left_on="end", right_index=True, how="inner")
    df["asof"] = df["end"] + pd.Timedelta(days=1)
    df["f"] = [fare_yoy(e, a) for e, a in zip(df["end"], df["asof"])]
    return df.reset_index(drop=True), full


_CPI = None


def fare_yoy(end, asof):
    """Airline-fare CPI YoY for quarter `end`, using only months published before `asof`.

    At quarter end only months 1-2 of the quarter are public, so the signal is the mean
    log YoY change over those months (fewer if BLS skipped a month, e.g. Oct 2025).
    """
    global _CPI
    if _CPI is None:
        _CPI = pd.read_csv(P / "bls_airfare_monthly.csv", parse_dates=["month", "available_from"]).set_index("month")
    q_start = (end - pd.offsets.QuarterBegin(1, startingMonth=1)).normalize()
    vals = []
    for k in range(3):
        m = q_start + pd.DateOffset(months=k)
        m0 = m - pd.DateOffset(years=1)
        if m in _CPI.index and m0 in _CPI.index and _CPI.loc[m, "available_from"] < asof:
            vals.append(np.log(_CPI.loc[m, "cpi_airfare"] / _CPI.loc[m0, "cpi_airfare"]))
    return float(np.mean(vals)) if vals else np.nan


def last_reported(df, ticker, asof):
    """y and x of the latest quarter whose revenue was filed before `asof`."""
    h = df[(df["ticker"] == ticker) & (df["filed"] < asof)]
    if h.empty:
        return np.nan, np.nan, np.nan
    r = h.sort_values("end").iloc[-1]
    return r["y"], r["x"], r["f"]


def fit_ols(X, y):
    X = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def run():
    df, _ = load()
    lr = [last_reported(df, r.ticker, r.asof) for r in df.itertuples()]
    df["y_last"] = [a for a, _, _ in lr]
    df["x_last"] = [b for _, b, _ in lr]
    df["f_last"] = [c for _, _, c in lr]
    df["dfare"] = df["f"] - df["f_last"]       # acceleration in airfare inflation
    df["dy"] = df["y"] - df["y_last"]          # acceleration in revenue growth
    df["dx"] = df["x"] - df["x_last"]          # acceleration in TSA growth, same quarters
    out = []
    for r in df.itertuples():
        assert r.filed_lag4 < r.asof, "year-ago base not yet public"
        train = df[(df["filed"] < r.asof)].dropna(subset=["y_last"])
        rec = {"ticker": r.ticker, "end": r.end, "asof": r.asof, "actual": r.val,
               "base": r.rev_lag4, "x": r.x, "y": r.y, "n_train": len(train)}
        rec["B1"] = r.rev_lag4
        rec["B2"] = r.rev_lag4 * np.exp(r.y_last) if not np.isnan(r.y_last) else np.nan
        if len(train) >= MIN_TRAIN and not np.isnan(r.y_last):
            a, b = fit_ols(train[["x"]].values, train["y"].values)
            rec["M1"] = r.rev_lag4 * np.exp(a + b * r.x)
            a2, b2, c2 = fit_ols(train[["x", "y_last"]].values, train["y"].values)
            rec["M2"] = r.rev_lag4 * np.exp(a2 + b2 * r.x + c2 * r.y_last)
            # M3 (pre-committed last variant): B2 + b3 * (change in TSA growth).
            # No intercept: with no TSA change, the nowcast collapses to B2.
            tr = train.dropna(subset=["dx"])
            b3 = float(np.dot(tr["dx"], tr["dy"]) / np.dot(tr["dx"], tr["dx"]))
            rec["M3"] = r.rev_lag4 * np.exp(r.y_last + b3 * r.dx)
            rec.update({"m1_a": a, "m1_b": b, "m2_b": b2, "m2_c": c2, "m3_b": b3,
                        "dx": r.dx, "dy": r.dy, "dfare": r.dfare})
            # M4 (pre-committed FINAL variant): B2 + volume change + fare change.
            # Revenue = volume x price, so the two accelerations enter additively in logs.
            tr4 = train.dropna(subset=["dx", "dfare"])
            if not np.isnan(r.dfare) and len(tr4) >= MIN_TRAIN:
                Z = tr4[["dx", "dfare"]].values
                bx4, bf4 = np.linalg.lstsq(Z, tr4["dy"].values, rcond=None)[0]
                rec["M4"] = r.rev_lag4 * np.exp(r.y_last + bx4 * r.dx + bf4 * r.dfare)
                rec.update({"m4_bx": bx4, "m4_bf": bf4})
        out.append(rec)
    res = pd.DataFrame(out)
    res["event_excluded"] = [(t, e) in EVENT_EXCLUDE for t, e in zip(res["ticker"], res["end"])]
    return res


def score(res, models=("B1", "B2", "M1", "M2", "M3", "M4")):
    rows = []
    for m in models:
        e = (res[m] - res["actual"]) / res["actual"]
        rows.append({"model": m, "n": int(e.notna().sum()),
                     "MAPE_%": round(100 * e.abs().mean(), 2),
                     "median_APE_%": round(100 * e.abs().median(), 2),
                     "bias_%": round(100 * e.mean(), 2)})
    return pd.DataFrame(rows)


def main():
    res = run()
    res.to_csv(P / "backtest_predictions.csv", index=False)
    ev = res[(res["end"] >= EVAL_START) & res[["B2", "M1", "M2", "M3", "M4"]].notna().all(axis=1)]
    head = ev[~ev["event_excluded"]]
    print(f"Eval window {EVAL_START.date()} .. {ev['end'].max().date()}  "
          f"airline-quarters={len(head)} (excl. {int(ev['event_excluded'].sum())} ALK merger quarters)\n")
    s = score(head)
    print(s.to_string(index=False))
    print("\nMAPE % by airline:")
    by = head.groupby("ticker").apply(
        lambda g: pd.Series({m: round(100 * ((g[m] - g["actual"]) / g["actual"]).abs().mean(), 2)
                             for m in ["B1", "B2", "M1", "M2", "M3", "M4"]}), include_groups=False)
    print(by.to_string())
    print("\nMAPE % by year:")
    head = head.assign(year=head["end"].dt.year)
    by_y = head.groupby("year").apply(
        lambda g: pd.Series({m: round(100 * ((g[m] - g["actual"]) / g["actual"]).abs().mean(), 2)
                             for m in ["B1", "B2", "M1", "M2", "M3", "M4"]}), include_groups=False)
    print(by_y.to_string())
    # Direction test: does the sign of the TSA change call the sign of the revenue change?
    d = head[(head["dx"].abs() > 0)]
    hits = int((np.sign(d["dx"]) == np.sign(d["dy"])).sum())
    from math import comb
    n = len(d)
    p_val = sum(comb(n, k) for k in range(hits, n + 1)) / 2 ** n
    print(f"\nDirection: sign(dTSA) == sign(dRevenueGrowth) in {hits}/{n} = {hits/n:.1%} "
          f"(one-sided binomial p={p_val:.4f} vs coin flip)")
    m3 = 100 * ((head["M3"] - head["actual"]) / head["actual"]).abs()
    b2 = 100 * ((head["B2"] - head["actual"]) / head["actual"]).abs()
    wins = int((m3 < b2).sum())
    print(f"M3 beats B2 in {wins}/{len(head)} airline-quarters; mean APE gain {(b2 - m3).mean():.2f} pts")
    last = res.dropna(subset=["m1_b"]).iloc[-1]
    print(f"Latest M3 slope b3 = {last.m3_b:.3f}")
    m4 = 100 * ((head["M4"] - head["actual"]) / head["actual"]).abs()
    w4 = int((m4 < b2).sum())
    from math import comb as _c
    p4 = sum(_c(len(head), k) for k in range(w4, len(head) + 1)) / 2 ** len(head)
    dd = head[head["dfare"].abs() > 0]
    hf = int((np.sign(dd["dfare"]) == np.sign(dd["dy"])).sum())
    pf = sum(_c(len(dd), k) for k in range(hf, len(dd) + 1)) / 2 ** len(dd)
    print(f"M4 beats B2 in {w4}/{len(head)} (sign-test p={p4:.4f}); mean APE gain {(b2 - m4).mean():.2f} pts")
    print(f"Fare direction: sign(dFare)==sign(dRevGrowth) in {hf}/{len(dd)} = {hf/len(dd):.1%} (p={pf:.4f})")
    l4 = res.dropna(subset=["m4_bx"]).iloc[-1]
    print(f"Latest M4: b_volume={l4.m4_bx:.3f}, b_fare={l4.m4_bf:.3f}")
    print(f"\nLatest M1 fit: y = {last.m1_a:.4f} + {last.m1_b:.3f}*x  (n_train={last.n_train})")
    json.dump({"headline": s.to_dict("records"), "eval_start": str(EVAL_START.date()),
               "n": int(len(head)), "direction_hits": hits, "direction_n": n,
               "direction_p": p_val, "m3_beats_b2": wins,
               "m4_beats_b2": w4, "m4_sign_p": p4, "fare_dir_hits": hf, "fare_dir_n": len(dd), "fare_dir_p": pf}, open(P / "backtest_summary.json", "w"), indent=2)


if __name__ == "__main__":
    main()
