"""Download airline earnings-release exhibits (8-K Item 2.02, Exhibit 99.x) from SEC EDGAR.

Run on your own computer:
    pip install requests
    python src/fetch_8k.py

Saves to data/raw/8k/<TICKER>/<filing_date>_<accession>_<file>.htm plus
data/raw/8k/8k_provenance.csv (URL, filing date, SHA-256). Zip data/raw/8k and attach it.
Respects SEC fair access: declared User-Agent, <= ~5 requests/second.
"""
import csv
import hashlib
import os
import sys
import time
from datetime import datetime, timezone

import requests

UA = {"User-Agent": "Amarnath Reddy Ganta research amarnathreddyganta5@gmail.com"}
AIRLINES = {"DAL": 27904, "UAL": 100517, "AAL": 6201, "LUV": 92380, "ALK": 766421, "JBLU": 1158463}
START = "2022-01-01"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "8k")


def get(url):
    time.sleep(0.2)
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    return r


def earnings_8ks(cik):
    sub = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json()
    rec = sub["filings"]["recent"]
    for form, date, acc, items in zip(rec["form"], rec["filingDate"], rec["accessionNumber"], rec["items"]):
        if form == "8-K" and "2.02" in (items or "") and date >= START:
            yield date, acc


def exhibits(cik, acc):
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
    items = get(f"{base}/index.json").json()["directory"]["item"]
    names = [i["name"] for i in items if i["name"].lower().endswith((".htm", ".html", ".txt"))]
    ex = [n for n in names if "99" in n.lower() and "index" not in n.lower()]
    return base, ex


def main():
    rows, failed = [], 0
    for tick, cik in AIRLINES.items():
        d = os.path.join(OUT, tick)
        os.makedirs(d, exist_ok=True)
        n = 0
        try:
            for date, acc in earnings_8ks(cik):
                base, ex = exhibits(cik, acc)
                if not ex:
                    print(f"[WARN] {tick} {date} {acc}: no exhibit 99 file found")
                    failed += 1
                    continue
                for name in ex:
                    body = get(f"{base}/{name}").content
                    fn = f"{date}_{acc}_{name}"
                    with open(os.path.join(d, fn), "wb") as f:
                        f.write(body)
                    rows.append({"ticker": tick, "cik": cik, "filing_date": date, "accession": acc,
                                 "file": f"{tick}/{fn}", "url": f"{base}/{name}",
                                 "sha256": hashlib.sha256(body).hexdigest(),
                                 "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
                n += 1
            print(f"[ok]   {tick}: {n} earnings 8-Ks since {START}")
        except Exception as e:
            print(f"[FAIL] {tick}: {e}")
            failed += 1
    with open(os.path.join(OUT, "8k_provenance.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["ticker"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nSaved {len(rows)} exhibit files to {os.path.abspath(OUT)}")
    if failed:
        print("Some downloads failed. Paste the [FAIL]/[WARN] lines into the chat.")
        sys.exit(1)


if __name__ == "__main__":
    main()
