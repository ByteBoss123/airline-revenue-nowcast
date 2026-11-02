"""Parse TSA checkpoint tables copied from tsa.gov into one validated daily CSV.

Year is taken from each row's date, never from the file name or header,
so a mislabeled header (e.g. "025") cannot shift data into the wrong year.
"""
import hashlib
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "tsa"
OUT = ROOT / "data" / "processed"
ROW = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})\s+([\d,]+)\s*$")


def parse_file(path: Path) -> pd.DataFrame:
    rows, bad = [], []
    text = path.read_text(encoding="utf-8")
    is_current = text.lstrip().startswith("Passenger travel numbers are updated")
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not re.match(r"^\d{1,2}/\d{1,2}/\d{4}", line):
            continue  # headers / notes (e.g. "2023 TSA checkpoint travel numbers")
        m = ROW.match(line)
        if not m:
            bad.append((i, line))
            continue
        mo, d, y, n = m.groups()
        rows.append({"date": date(int(y), int(mo), int(d)),
                     "travelers": int(n.replace(",", ""))})
    if bad:
        raise ValueError(f"{path.name}: unparseable lines {bad[:5]}")
    df = pd.DataFrame(rows)
    df["source_file"] = path.name
    # Archived years carry TSA's note that numbers were revised (Known Crewmembers,
    # late flights). The current-year page is the first-print vintage.
    df["vintage"] = "current_page" if is_current else "archived_revised"
    return df


def validate(df: pd.DataFrame) -> dict:
    report = {}
    dupes = df["date"].duplicated().sum()
    assert dupes == 0, f"{dupes} duplicate dates"
    full = pd.date_range(df["date"].min(), df["date"].max(), freq="D").date
    missing = sorted(set(full) - set(df["date"]))
    report["first_date"] = str(df["date"].min())
    report["last_date"] = str(df["date"].max())
    report["rows"] = len(df)
    report["missing_days"] = len(missing)
    report["missing_years"] = sorted({d.year for d in missing})
    report["min_travelers"] = int(df["travelers"].min())
    report["max_travelers"] = int(df["travelers"].max())
    assert (df["travelers"] > 0).all(), "non-positive count"
    return report, missing


def main():
    files = sorted(RAW.glob("*.txt"))
    parts = [parse_file(p) for p in files]
    df = pd.concat(parts).sort_values("date").reset_index(drop=True)
    report, missing = validate(df)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "tsa_daily.csv", index=False)

    prov = []
    for p, part in zip(files, parts):
        prov.append({
            "file": p.name,
            "years_in_file": ",".join(sorted({str(d.year) for d in part["date"]})),
            "rows": len(part),
            "vintage": part["vintage"].iloc[0],
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "source": "https://www.tsa.gov/travel/passenger-volumes (copied by user from browser)",
            "ingested_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    pd.DataFrame(prov).sort_values("years_in_file").to_csv(OUT / "tsa_provenance.csv", index=False)

    for k, v in report.items():
        print(f"{k}: {v}")
    print(pd.DataFrame(prov)[["years_in_file", "rows", "vintage"]].sort_values("years_in_file").to_string(index=False))
    return 0 if not missing else 2


if __name__ == "__main__":
    sys.exit(main())
