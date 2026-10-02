"""Step 2: every fatal crash, 2010-2024, as daily counts.

    ./venv/bin/python prepare.py   -> results/daily.csv, results/crashes_by_year.csv

One row per date and group: states that change their clocks, and Arizona plus Hawaii, which do not (Arizona's Navajo
Nation does observe daylight saving time; its crashes cannot be separated reliably here and stay in Arizona).
Counts are split by time of day, because the spring change moves an hour of daylight from morning to evening.
Crashes with an unknown day are counted in crashes_by_year.csv and left out of the daily table.
"""
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"
R = HERE / "results"
NO_DST = {4: "AZ", 15: "HI"}                                           # FIPS state codes


def nth_sunday(year, month, n):
    d = date(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)                          # first Sunday
    return d + timedelta(weeks=n - 1)


def clock_changes(years):
    """Since 2007: second Sunday of March (spring forward), first Sunday of November (fall back)."""
    return pd.DataFrame([{"year": y, "spring": nth_sunday(y, 3, 2), "fall": nth_sunday(y, 11, 1)} for y in years])


def main():
    rows = []
    for y in range(2010, 2025):
        z = zipfile.ZipFile(RAW / f"FARS{y}NationalCSV.zip")
        name = next(n for n in z.namelist() if n.lower().endswith("accident.csv"))
        a = pd.read_csv(z.open(name), encoding="latin-1", usecols=lambda c: c.upper() in {"STATE", "ST_CASE", "YEAR", "MONTH", "DAY", "HOUR", "FATALS"})
        a.columns = [c.upper() for c in a.columns]
        rows.append(a)
    a = pd.concat(rows, ignore_index=True)
    by_year = a.groupby("YEAR").agg(crashes=("ST_CASE", "size"), deaths=("FATALS", "sum"),
                                    unknown_day=("DAY", lambda s: int((s == 99).sum())), unknown_hour=("HOUR", lambda s: int((s == 99).sum())))
    by_year.reset_index().rename(columns={"YEAR": "year"}).to_csv(R / "crashes_by_year.csv", index=False)

    a = a[(a["DAY"] != 99) & (a["MONTH"] != 99)].copy()
    a["date"] = pd.to_datetime(dict(year=a["YEAR"], month=a["MONTH"], day=a["DAY"]))
    a["group"] = a["STATE"].map(NO_DST).notna().map({True: "AZ+HI", False: "DST states"})
    h = a["HOUR"]
    a["period"] = pd.cut(h.where(h != 99), [-1, 4, 9, 14, 20, 23], labels=["night 0-4", "morning 5-9", "midday 10-14", "evening 15-20", "late 21-23"])
    daily = a.pivot_table(index=["date", "group"], columns="period", values="ST_CASE", aggfunc="size", fill_value=0, observed=False)
    daily["crashes"] = a.groupby(["date", "group"]).size()
    daily["deaths"] = a.groupby(["date", "group"])["FATALS"].sum()
    full = pd.MultiIndex.from_product([pd.date_range("2010-01-01", "2024-12-31"), ["DST states", "AZ+HI"]], names=["date", "group"])
    daily = daily.reindex(full, fill_value=0).reset_index()
    daily.columns = [str(c) for c in daily.columns]
    ch = clock_changes(range(2010, 2025))
    daily["year"] = daily["date"].dt.year
    daily = daily.merge(ch, on="year")
    daily["days_from_spring"] = (daily["date"] - pd.to_datetime(daily["spring"])).dt.days
    daily["days_from_fall"] = (daily["date"] - pd.to_datetime(daily["fall"])).dt.days
    daily["dow"] = daily["date"].dt.dayofweek
    daily.drop(columns=["spring", "fall"]).to_csv(R / "daily.csv", index=False)
    print(by_year.to_string())
    print(daily.groupby("group")[["crashes", "deaths"]].sum())


if __name__ == "__main__":
    main()
