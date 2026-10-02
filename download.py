"""Step 1: NHTSA's Fatality Analysis Reporting System (FARS), every fatal crash in the US, 2010-2024.

    ./venv/bin/python download.py    -> data/raw/FARS{year}NationalCSV.zip (not committed), results/pull.json

FARS is a census of crashes on public roads in which someone died within 30 days. 2024 is the latest annual file.
"""
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"
YEARS = range(2010, 2025)
URL = "https://static.nhtsa.gov/nhtsa/downloads/FARS/{y}/National/FARS{y}NationalCSV.zip"


def fetch(y):
    out = RAW / f"FARS{y}NationalCSV.zip"
    if not out.exists():
        req = urllib.request.Request(URL.format(y=y), headers={"User-Agent": "Mozilla/5.0"})
        out.write_bytes(urllib.request.urlopen(req, timeout=600).read())
    return out.stat().st_size


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(5) as pool:
        sizes = list(pool.map(fetch, YEARS))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "pull.json").write_text(json.dumps({"source": "NHTSA FARS national CSV files", "years": [min(YEARS), max(YEARS)],
                                                            "total_mb": round(sum(sizes) / 1e6)}, indent=2) + "\n")
    print(sum(sizes) // 1_000_000, "MB")


if __name__ == "__main__":
    main()
