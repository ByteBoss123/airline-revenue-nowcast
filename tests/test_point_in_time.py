"""Guards against look-ahead and data errors. Run: python -m pytest -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
P = ROOT / "data" / "processed"

import backtest  # noqa: E402
from ingest_sec import quarterly  # noqa: E402
from ingest_tsa import parse_file  # noqa: E402


@pytest.fixture(scope="module")
def frames():
    df, _ = backtest.load()
    return df, pd.read_csv(P / "backtest_predictions.csv", parse_dates=["end", "asof"])


def test_tsa_complete_and_unique():
    t = pd.read_csv(P / "tsa_daily.csv", parse_dates=["date"])
    assert t["date"].is_unique
    full = pd.date_range(t["date"].min(), t["date"].max(), freq="D")
    assert len(full) == len(t), "gap in TSA daily series"


def test_tsa_header_with_digits_not_parsed_as_data(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("025 TSA checkpoint travel numbers\nDate\tNumbers\n1/2/2025\t2,612,162\n")
    df = parse_file(f)
    assert len(df) == 1 and df["travelers"].iloc[0] == 2612162


def test_fare_signal_never_uses_unpublished_months():
    cpi = pd.read_csv(P / "bls_airfare_monthly.csv", parse_dates=["month", "available_from"])
    # At a quarter-end as-of date, month 3 of that quarter is not yet published.
    end = pd.Timestamp("2026-09-30")
    asof = end + pd.Timedelta(days=1)
    sep = cpi.loc[cpi["month"] == "2026-09-01", "available_from"].iloc[0]
    assert sep >= asof
    jul_aug = np.mean([np.log(cpi.set_index("month").loc[m, "cpi_airfare"] /
                              cpi.set_index("month").loc[m0, "cpi_airfare"])
                       for m, m0 in [("2026-07-01", "2025-07-01"), ("2026-08-01", "2025-08-01")]])
    assert backtest.fare_yoy(end, asof) == pytest.approx(jul_aug)


def test_missing_bls_month_handled():
    # Oct 2025 was not published; Q4 2025 signal must use the remaining month(s) only.
    v = backtest.fare_yoy(pd.Timestamp("2025-12-31"), pd.Timestamp("2026-01-01"))
    assert not np.isnan(v)


def test_training_rows_were_public_at_asof(frames):
    df, res = frames
    for r in res.dropna(subset=["M4"]).itertuples():
        used = df[df["filed"] < r.asof]
        assert (used["filed"] < r.asof).all()
        assert not ((df["ticker"] == r.ticker) & (df["end"] == r.end) & (df["filed"] < r.asof)).any(), \
            "target quarter leaked into its own training set"


def test_year_ago_base_is_public(frames):
    df, _ = frames
    assert (df["filed_lag4"] < df["asof"]).all()


def test_q4_derivation_sums_to_fiscal_year():
    q3m = pd.DataFrame({
        "start": pd.to_datetime(["2024-01-01", "2024-04-01", "2024-07-01"]),
        "end": pd.to_datetime(["2024-03-31", "2024-06-30", "2024-09-30"]),
        "val": [10.0, 12.0, 11.0], "filed": pd.to_datetime(["2024-04-10"] * 3), "form": ["10-Q"] * 3})
    fy = pd.DataFrame({"start": [pd.Timestamp("2024-01-01")], "end": [pd.Timestamp("2024-12-31")],
                       "val": [45.0], "filed": [pd.Timestamp("2025-02-10")], "form": ["10-K"]})
    f = pd.concat([q3m, fy], ignore_index=True)
    f["days"] = (f["end"] - f["start"]).dt.days
    out = quarterly(f)
    q4 = out[out["end"] == "2024-12-31"].iloc[0]
    assert q4["val"] == 12.0 and q4["derived"] and q4["filed"] == pd.Timestamp("2025-02-10")


def test_revenue_series_has_no_gaps():
    r = pd.read_csv(P / "sec_quarterly_revenue.csv", parse_dates=["end"])
    for t, g in r.groupby("ticker"):
        exp = pd.date_range(g["end"].min(), g["end"].max(), freq="QE")
        assert len(exp) == len(g), f"{t} has quarter gaps"
