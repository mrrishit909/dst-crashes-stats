"""Steps 3-4: does the week after a clock change have more fatal crashes, and is that more than chance?

    ./venv/bin/python analyze.py   -> results/models.csv, placebo.csv, time_of_day.csv

Model: daily fatal crashes in a window of 4 weeks either side of the change, each year, with quasi-Poisson errors
(counts, allowing overdispersion):  crashes ~ week_after + year + day of week + days from the change (trend).
week_after is the 7 days starting on the Sunday of the change. exp(coefficient) is the rate ratio.
Placebo: the same model around every other Sunday of the year (outside 5 weeks of either change) gives the spread
of "week after" estimates that arise with no clock change at all.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

HERE = Path(__file__).parent
R = HERE / "results"
FORMULA = "{y} ~ week_after + C(year) + C(dow) + t"


def window(d, centre_col, days=28):
    w = d[d[centre_col].between(-days, days + 6)].copy()
    w["t"] = w[centre_col]
    w["week_after"] = w[centre_col].between(0, 6).astype(int)
    return w


def fit(w, y="crashes"):
    import statsmodels.api as sm
    m = smf.glm(FORMULA.format(y=y), w, family=sm.families.Poisson()).fit(scale="X2")
    b, se = m.params["week_after"], m.bse["week_after"]
    return {"rate_ratio": np.exp(b), "lo95": np.exp(b - 1.96 * se), "hi95": np.exp(b + 1.96 * se), "p": m.pvalues["week_after"],
            "coef": b, "se": se, "dispersion": m.scale, "days": len(w), "events": int(w[y].sum())}


def fit_with(w, extra, y="crashes"):
    """The same model with one more term."""
    import statsmodels.api as sm
    m = smf.glm(FORMULA.format(y=y) + " + " + extra, w, family=sm.families.Poisson()).fit(scale="X2")
    b, se = m.params["week_after"], m.bse["week_after"]
    return {"rate_ratio": np.exp(b), "lo95": np.exp(b - 1.96 * se), "hi95": np.exp(b + 1.96 * se), "p": m.pvalues["week_after"],
            "coef": b, "se": se, "dispersion": m.scale, "days": len(w), "events": int(w[y].sum())}


def main():
    d = pd.read_csv(R / "daily.csv", parse_dates=["date"])
    out = []
    for group in ["DST states", "AZ+HI"]:
        g = d[d["group"] == group]
        for change, col in [("spring forward", "days_from_spring"), ("fall back", "days_from_fall")]:
            out.append({"group": group, "change": change, "outcome": "crashes", **fit(window(g, col))})
            out.append({"group": group, "change": change, "outcome": "deaths", **fit(window(g, col), "deaths")})
    models = pd.DataFrame(out)
    models.round(6).to_csv(R / "models.csv", index=False)

    dst = d[d["group"] == "DST states"]
    tod = []
    for period in ["night 0-4", "morning 5-9", "midday 10-14", "evening 15-20", "late 21-23"]:
        w = window(dst, "days_from_spring").rename(columns={period: "y_period"})
        no_stp = w[~((w["date"].dt.month == 3) & w["date"].dt.day.isin([17, 18]))]
        tod.append({"period": period, **fit(w, "y_period"),
                    "rate_ratio_without_st_patricks": np.exp(fit(no_stp, "y_period")["coef"]), "p_without_st_patricks": fit(no_stp, "y_period")["p"]})
    pd.DataFrame(tod).round(6).to_csv(R / "time_of_day.csv", index=False)

    # robustness for the spring change: things in the same weeks that could fake it
    w0 = window(dst, "days_from_spring")
    w0["st_patricks"] = ((w0["date"].dt.month == 3) & (w0["date"].dt.day.isin([17, 18]))).astype(int)   # the night of the 17th runs past midnight
    rob = [{"check": "main model", **fit(w0)},
           {"check": "without 2020 (lockdown began the next week)", **fit(w0[w0["year"] != 2020])},
           {"check": "St Patrick's Day (17-18 March) as its own term", **fit_with(w0, "st_patricks")},
           {"check": "without St Patrick's Day (17-18 March)", **fit(w0[w0["st_patricks"] == 0])},
           {"check": "window of 3 weeks, not 4", **fit(window(dst, "days_from_spring", 21))},
           {"check": "workdays only (Mon-Fri)", **fit(w0[w0["dow"] < 5])}]
    pd.DataFrame(rob).round(6).to_csv(R / "robustness.csv", index=False)
    print(pd.DataFrame(rob)[["check", "rate_ratio", "lo95", "hi95", "p", "days"]].round(4).to_string(index=False))

    # placebo: every Sunday at least 5 weeks from both changes, using the same window and model
    sundays = dst.loc[dst["dow"] == 6, ["date", "days_from_spring", "days_from_fall"]]
    sundays = sundays[(sundays["days_from_spring"].abs() > 35) & (sundays["days_from_fall"].abs() > 35)
                      & (sundays["date"] >= "2010-02-01") & (sundays["date"] <= "2024-11-30")]
    pl = []
    for s in sundays["date"].dt.dayofyear.unique():                     # one placebo per day-of-year, pooled over years
        cand = dst.copy()
        sun = cand.loc[(cand["dow"] == 6) & (cand["date"].dt.dayofyear.between(s - 3, s + 3)), ["year", "date"]].groupby("year")["date"].min()
        cand["placebo_day"] = (cand["date"] - cand["year"].map(sun)).dt.days
        w = window(cand.dropna(subset=["placebo_day"]), "placebo_day")
        if w["year"].nunique() < 12:
            continue
        pl.append({"sunday_day_of_year": int(s), **fit(w)})
    placebo = pd.DataFrame(pl).drop_duplicates("rate_ratio")
    placebo.round(6).to_csv(R / "placebo.csv", index=False)
    true_rr = models.query("group == 'DST states' and change == 'spring forward' and outcome == 'crashes'")["rate_ratio"].iloc[0]
    share = (placebo["rate_ratio"] >= true_rr).mean()
    print(models[["group", "change", "outcome", "rate_ratio", "lo95", "hi95", "p", "dispersion", "events"]].round(4).to_string(index=False))
    print(pd.read_csv(R / "time_of_day.csv")[["period", "rate_ratio", "lo95", "hi95", "p", "events"]].round(4).to_string(index=False))
    print(f"placebo Sundays: {len(placebo)}; share with a week-after rate ratio >= the spring change's {true_rr:.4f}: {share:.3f}")


if __name__ == "__main__":
    main()
