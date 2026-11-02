"""
Download the official source data for the airline revenue nowcast.

Run on your own computer (not in the chat workspace):
    pip install requests pandas lxml
    python fetch_data.py

Creates a folder `raw_data/` with:
    tsa_checkpoint_<year>.csv   official TSA daily checkpoint counts (tsa.gov)
    sec_companyfacts_<TICKER>.json   official SEC XBRL company facts (data.sec.gov)
    provenance.csv              source URL, download time (UTC), SHA-256 of every file

Then zip `raw_data/` and attach it in the chat.
"""
import datetime as dt
import hashlib
import io
import os
import sys

import pandas as pd
import requests

OUT = "raw_data"
# SEC requires a descriptive User-Agent with a contact email.
SEC_UA = "Amarnath Reddy Ganta research amarnathreddyganta5@gmail.com"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# CIKs to verify: the script checks the company name in each file.
AIRLINES = {
    "DAL": ("0000027904", "delta"),
    "UAL": ("0000100517", "united"),
    "AAL": ("0000006201", "american"),
    "LUV": ("0000092380", "southwest"),
    "ALK": ("0000766421", "alaska"),
    "JBLU": ("0001158463", "jetblue"),
}
TSA_YEARS = range(2019, 2027)

provenance = []


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def log(name, url, content):
    provenance.append({
        "file": name,
        "source_url": url,
        "downloaded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sha256": sha256(content),
        "bytes": len(content),
    })


def fetch_tsa():
    current = dt.date.today().year
    for year in TSA_YEARS:
        url = ("https://www.tsa.gov/travel/passenger-volumes" if year == current
               else f"https://www.tsa.gov/travel/passenger-volumes/{year}")
        try:
            r = requests.get(url, headers={"User-Agent": BROWSER_UA}, timeout=30)
            r.raise_for_status()
            tables = pd.read_html(io.StringIO(r.text))
            if not tables:
                raise ValueError("no table on page")
            df = tables[0]
            df.columns = [str(c).strip().lower() for c in df.columns]
            name = f"tsa_checkpoint_{year}.csv"
            path = os.path.join(OUT, name)
            df.to_csv(path, index=False)
            with open(path, "rb") as f:
                log(name, url, f.read())
            print(f"[ok]   TSA {year}: {len(df)} rows, columns={list(df.columns)}")
        except Exception as e:
            print(f"[FAIL] TSA {year} ({url}): {e}")


def fetch_sec():
    for ticker, (cik, expect) in AIRLINES.items():
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        try:
            r = requests.get(url, headers={"User-Agent": SEC_UA}, timeout=60)
            r.raise_for_status()
            data = r.json()
            entity = data.get("entityName", "")
            if expect not in entity.lower():
                print(f"[WARN] {ticker}: CIK {cik} returned '{entity}', expected '{expect}'. Not saved.")
                continue
            name = f"sec_companyfacts_{ticker}.json"
            with open(os.path.join(OUT, name), "wb") as f:
                f.write(r.content)
            log(name, url, r.content)
            print(f"[ok]   SEC {ticker}: {entity}")
        except Exception as e:
            print(f"[FAIL] SEC {ticker} ({url}): {e}")


def main():
    os.makedirs(OUT, exist_ok=True)
    fetch_tsa()
    fetch_sec()
    pd.DataFrame(provenance).to_csv(os.path.join(OUT, "provenance.csv"), index=False)
    print(f"\nSaved {len(provenance)} files to ./{OUT}/ (see provenance.csv).")
    if len(provenance) < len(TSA_YEARS) + len(AIRLINES):
        print("Some downloads failed. Paste the [FAIL]/[WARN] lines into the chat.")
        sys.exit(1)


if __name__ == "__main__":
    main()
