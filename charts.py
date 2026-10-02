"""Step 5: charts.   ./venv/bin/python charts.py -> charts/01_event.png, 02_placebo.png, 03_time_of_day.png, 04_robustness.png"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
R = HERE / "results"
INK, DIM, GRID, BG, BLUE, ORANGE, GRAY = "#f2f2f0", "#8a8a87", "#1d1d1d", "#0b0b0b", "#3987e5", "#d95926", "#9a9a96"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "text.color": INK,
                     "axes.edgecolor": "#3a3a3a", "axes.labelcolor": DIM, "xtick.color": DIM, "ytick.color": DIM,
                     "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 1,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 11, "axes.titlesize": 13,
                     "axes.titlelocation": "left", "axes.titlepad": 12})


def save(fig, name):
    fig.tight_layout(); fig.savefig(HERE / "charts" / name, dpi=150); plt.close(fig)


def main():
    (HERE / "charts").mkdir(exist_ok=True)
    d = pd.read_csv(R / "daily.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [2.2, 1]})
    for ax, group, col in [(axes[0], "DST states", BLUE), (axes[1], "AZ+HI", ORANGE)]:
        g = d[(d["group"] == group) & d["days_from_spring"].between(-28, 34)].copy()
        g["week"] = np.floor(g["days_from_spring"] / 7).astype(int)
        wk = g.groupby("week")["crashes"].sum() / g["year"].nunique() / 7       # mean crashes per day in that week
        base = wk.drop(0).mean()
        ax.bar(wk.index, 100 * (wk / base - 1), color=[col if w == 0 else GRAY for w in wk.index], width=0.7)
        others = wk.drop(0)
        slope, icept = np.polyfit(others.index, 100 * (others / base - 1), 1)     # spring's own rise, from the other weeks
        xs = np.array([wk.index.min() - 0.4, wk.index.max() + 0.4])
        ax.plot(xs, icept + slope * xs, color=INK, linestyle="--", linewidth=1, label="trend in the other weeks")
        ax.axhline(0, color=DIM, linewidth=1)
        ax.set_xticks(wk.index, [("change\nweek" if w == 0 else f"{w:+d}") for w in wk.index], fontsize=9)
        ax.set_title(("States that change clocks" if group == "DST states" else "Arizona + Hawaii (no change)"), fontsize=12)
        ax.set_ylim(-12, 12)
    axes[0].set_ylabel("fatal crashes per day vs the other weeks (%)")
    axes[0].legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper left")
    fig.suptitle("Fatal crashes in the weeks around the spring clock change, 2010-2024: raw averages; spring brings its own rise", x=0.01, ha="left", fontsize=13, color=INK)
    save(fig, "01_event.png")

    pl = pd.read_csv(R / "placebo.csv")
    rr = pd.read_csv(R / "models.csv").query("group == 'DST states' and change == 'spring forward' and outcome == 'crashes'")["rate_ratio"].iloc[0]
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.hist(100 * (pl["rate_ratio"] - 1), bins=30, color=GRAY)
    ax.axvline(100 * (rr - 1), color=ORANGE, linewidth=2.5)
    ax.text(100 * (rr - 1) - 0.2, ax.get_ylim()[1] * 0.85, f"spring clock change\n+{100 * (rr - 1):.1f}%", color=INK, ha="right", fontsize=10)
    ax.set_xlabel("estimated change in fatal crashes in the week after a Sunday (%), same model")
    ax.set_ylabel("Sundays"); ax.grid(axis="x", visible=False)
    ax.set_title(f"None of {len(pl)} ordinary Sundays comes close: the placebo test")
    save(fig, "02_placebo.png")

    t = pd.read_csv(R / "time_of_day.csv")
    fig, ax = plt.subplots(figsize=(10, 3.6))
    y = np.arange(len(t))
    err = np.vstack([100 * (t["rate_ratio"] - t["lo95"]), 100 * (t["hi95"] - t["rate_ratio"])])
    ax.errorbar(100 * (t["rate_ratio"] - 1), y, xerr=err, fmt="o", color=BLUE, ecolor=DIM, capsize=3)
    ax.scatter(100 * (t["rate_ratio_without_st_patricks"] - 1), y + 0.18, color=ORANGE, s=22, label="without St Patrick's Day (17-18 March)")
    ax.axvline(0, color=DIM, linestyle="--", linewidth=1)
    ax.set_yticks(y, t["period"].str.replace("-", "–")); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
    ax.set_xlabel("change in fatal crashes in the week after spring forward (%, 95% CI)")
    ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper right")
    ax.set_title("By hour of the crash: the darker morning, and late evening")
    save(fig, "03_time_of_day.png")

    r = pd.read_csv(R / "robustness.csv").iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 3.6))
    y = np.arange(len(r))
    err = np.vstack([100 * (r["rate_ratio"] - r["lo95"]), 100 * (r["hi95"] - r["rate_ratio"])])
    ax.errorbar(100 * (r["rate_ratio"] - 1), y, xerr=err, fmt="o", color=BLUE, ecolor=DIM, capsize=3)
    for i, v in enumerate(r["rate_ratio"]):
        ax.text(100 * (v - 1), i + 0.28, f"+{100 * (v - 1):.1f}%", ha="center", color=INK, fontsize=9)
    ax.axvline(0, color=DIM, linestyle="--", linewidth=1)
    ax.set_yticks(y, r["check"]); ax.grid(axis="y", visible=False); ax.set_xlim(-1, 12)
    ax.set_xlabel("change in fatal crashes in the week after spring forward (%, 95% CI)")
    ax.set_title("The spring effect under every check")
    save(fig, "04_robustness.png")
    print("charts written")


if __name__ == "__main__":
    main()
