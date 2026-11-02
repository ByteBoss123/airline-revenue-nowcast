"""Parse the BLS CPI airline-fare series (CUUR0000SETG01, NSA) into a monthly CSV.

Point-in-time note: CPI for month m is published mid-month m+1. We treat it as
available on the 20th of m+1 (conservative). CPI-U NSA is not revised after
publication, so the downloaded values equal the first print.
BLS did not publish October 2025 (federal shutdown); that month stays missing.
"""
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bls"
OUT = ROOT / "data" / "processed"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    path = next(RAW.glob("*.xlsx"))
    raw = pd.read_excel(path, header=None)
    sid = raw.iloc[3, 1]
    assert sid == "CUUR0000SETG01", f"unexpected series {sid}"
    hdr = raw.index[raw[0] == "Year"][0]
    tbl = raw.iloc[hdr + 1:].copy()
    tbl.columns = raw.iloc[hdr].tolist()
    long = tbl.melt(id_vars="Year", value_vars=MONTHS, var_name="mon", value_name="cpi_airfare")
    long["month"] = pd.to_datetime(long["Year"].astype(int).astype(str) + "-" + long["mon"], format="%Y-%b")
    long = long.dropna(subset=["cpi_airfare"]).sort_values("month")
    long["available_from"] = (long["month"] + pd.offsets.MonthBegin(1)) + pd.Timedelta(days=19)
    long[["month", "cpi_airfare", "available_from"]].to_csv(OUT / "bls_airfare_monthly.csv", index=False)

    full = pd.date_range(long["month"].min(), long["month"].max(), freq="MS")
    missing = sorted(set(full) - set(long["month"]))
    pd.DataFrame([{
        "file": path.name, "series": sid, "seasonal_adjustment": "not seasonally adjusted",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": f"https://data.bls.gov/timeseries/{sid} (downloaded by user)",
        "missing_months": ";".join(m.strftime("%Y-%m") for m in missing),
        "ingested_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }]).to_csv(OUT / "bls_provenance.csv", index=False)
    print(f"{sid}: {len(long)} months {long['month'].min():%Y-%m}..{long['month'].max():%Y-%m}; "
          f"missing: {[m.strftime('%Y-%m') for m in missing]}")


if __name__ == "__main__":
    main()
