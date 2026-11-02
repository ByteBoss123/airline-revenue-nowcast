"""Extract point-in-time quarterly revenue from SEC XBRL company-facts files.

For each fiscal quarter we keep:
  - the value as FIRST filed (what an investor could see at that time), and
  - the filing date of that first appearance (used as the as-of cutoff).
Q4 is rarely tagged as its own 3-month fact; it is derived as FY minus the
three reported quarters, using only filings available when the 10-K was filed.

Run: python src/ingest_sec.py
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "sec"
OUT = ROOT / "data" / "processed"
TICKERS = {27904: "DAL", 100517: "UAL", 6201: "AAL", 92380: "LUV", 766421: "ALK", 1158463: "JBLU"}
TAGS = ["PassengerRevenue", "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"]


def load(path: Path) -> dict:
    t = path.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):])


def facts_frame(d: dict, tag: str) -> pd.DataFrame:
    node = d["facts"].get("us-gaap", {}).get(tag)
    if not node or "USD" not in node["units"]:
        return pd.DataFrame()
    df = pd.DataFrame(node["units"]["USD"])
    df = df[df["form"].isin(["10-Q", "10-K", "10-Q/A", "10-K/A"])].copy()
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    df["days"] = (df["end"] - df["start"]).dt.days
    return df


def first_filed(df: pd.DataFrame) -> pd.DataFrame:
    """For each (start, end) period, keep the earliest filing (first print)."""
    return df.sort_values("filed").groupby(["start", "end"], as_index=False).first()


def quarterly(df: pd.DataFrame) -> pd.DataFrame:
    q = first_filed(df[df["days"].between(80, 100)])
    q = q[["end", "val", "filed", "form"]].assign(derived=False)
    fy = first_filed(df[df["days"].between(350, 380)])
    rows = []
    for _, r in fy.iterrows():
        # The three quarters inside this fiscal year that end before the FY end
        inside = q[(q["end"] > r["start"]) & (q["end"] < r["end"] - pd.Timedelta(days=20))]
        if r["end"] in set(q["end"]) or len(inside) != 3:
            continue
        rows.append({"end": r["end"], "val": r["val"] - inside["val"].sum(),
                     "filed": r["filed"], "form": r["form"], "derived": True})
    out = pd.concat([q, pd.DataFrame(rows)], ignore_index=True)
    return out.sort_values("end").reset_index(drop=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    allq, prov = [], []
    for p in sorted(RAW.glob("*")):
        d = load(p)
        cik = int(d["cik"])
        tick = TICKERS.get(cik)
        if tick is None:
            print(f"[SKIP] {p.name}: CIK {cik} ({d.get('entityName')}) not in airline list")
            continue
        # Companies switch revenue tags over time (e.g. Delta: Revenues -> ASC 606 tag in 2018).
        # Merge all total-revenue tags, then keep the first filing for each period.
        frames = [facts_frame(d, t).assign(tag=t) for t in TAGS[1:]]
        f = pd.concat([x for x in frames if not x.empty], ignore_index=True)
        q = quarterly(f).assign(ticker=tick, tag="total_revenue")
        allq.append(q)
        prov.append({"file": p.name, "cik": cik, "ticker": tick, "entity": d.get("entityName"),
                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                     "source": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json (saved by user from browser)",
                     "ingested_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        print(f"[ok]   {tick}: {d.get('entityName')}")
    q = pd.concat(allq, ignore_index=True)
    q = q[q["end"] >= "2018-01-01"]
    for tick, g in q.groupby("ticker"):
        exp = pd.date_range(g["end"].min(), g["end"].max(), freq="QE")
        gap = sorted(set(exp) - set(g["end"]))
        if gap:
            print(f"[WARN] {tick}: missing quarters {[str(x.date()) for x in gap]}")
    q.to_csv(OUT / "sec_quarterly_revenue.csv", index=False)
    pd.DataFrame(prov).to_csv(OUT / "sec_provenance.csv", index=False)
    print(q.groupby(["ticker", "tag"]).agg(quarters=("end", "count"), first=("end", "min"),
                                           last=("end", "max"), derived_q4=("derived", "sum")).to_string())


if __name__ == "__main__":
    main()
