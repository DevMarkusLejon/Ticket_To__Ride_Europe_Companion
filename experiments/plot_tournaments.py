"""Render the repository's tournament figures with python -m experiments.plot_tournaments."""

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from experiments.europe_wait_comparison import TABLES, summarize

SOURCE = Path(__file__).resolve().parent
FIGURES = SOURCE.parent / "docs" / "figures"
PAPER, INK, MUTED, LINE = "#fcfbf8", "#173344", "#485c64", "#d3dbda"
BLUE, OCHRE = "#195b79", "#975320"
TABLE_NAMES = {"regular": "Three Regulars", "fast": "Three Fast Builders", "mixed": "Mixed table"}


def figure(title, subtitle, height):
    fig = plt.figure(figsize=(9.5, height), facecolor=PAPER)
    fig.text(0.04, 0.96, title, va="top", fontfamily="DejaVu Serif", fontsize=23, color=INK)
    fig.text(0.04, 0.96 - 0.50 / height, subtitle, va="top", fontsize=11, color=MUTED)
    return fig


def rule(fig, y):
    fig.add_artist(Line2D([0.04, 0.96], [y, y], transform=fig.transFigure, color=LINE, linewidth=0.8))


def save(fig, filename):
    fig.savefig(FIGURES / filename, dpi=160, facecolor=PAPER)
    plt.close(fig)


def wait_figure():
    deals = defaultdict(list)
    with (SOURCE / "europe_wait_pairs.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            deals[row["table"]].append({k: int(row[k]) for k in ("seat", "win_18", "win_25")})
    stats = {table: summarize(deals[table]) for table in TABLES}
    (n,) = {row["pairs"] for row in stats.values()}
    fig = figure("Waiting 18 or 25 turns", f"Hoard and Finish   ·   {n:,} matched deals per table   ·   Four-player Europe", 4.65)
    ax = fig.add_axes([0.52, 0.29, 0.44, 0.435], facecolor=PAPER)
    ax.set(xlim=(-7.5, 20), ylim=(-0.55, 2.55), yticks=[])
    ticks = [-5, 0, 5, 10, 15, 20]
    ax.set_xticks(ticks, [f"{t:+d}".replace("-", "−") if t else "0" for t in ticks])
    ax.tick_params(axis="x", length=0, colors=MUTED, labelsize=10, pad=6)
    ax.spines[:].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=LINE, linewidth=0.65)
    ax.axvline(0, color=MUTED, linewidth=1.25)
    ax.set_xlabel("Difference in percentage points", fontsize=10, color=MUTED, labelpad=6)
    for x, label, align in [(0.04, "Opponents", "left"), (0.31, "18 turns", "center"),
                            (0.43, "25 turns", "center"), (0.52, "Change in win rate", "left")]:
        fig.text(x, 0.76, label, ha=align, fontsize=11, weight="bold", color=INK)
    rule(fig, 0.735)
    for y, (table, row) in zip((2, 1, 0), stats.items()):
        row_y = fig.transFigure.inverted().transform(ax.transData.transform((0, y)))[1]
        fig.text(0.04, row_y, TABLE_NAMES[table], va="center", fontsize=12, color=INK)
        for x, wait in [(0.31, 18), (0.43, 25)]:
            rate = 100 * row[f"wins_{wait}"] / n
            fig.text(x, row_y, f"{rate:.1f}%", ha="center", va="center", fontsize=13, color=INK)
        delta, lo, hi = (row[key] for key in ("difference_pp", "lower_pp", "upper_pp"))
        color = BLUE if lo > 0 else OCHRE if hi < 0 else MUTED
        ax.errorbar(delta, y, xerr=[[delta - lo], [hi - delta]], fmt="o", ms=8,
                    color=color, mfc=color if lo * hi > 0 else PAPER, mew=1.7,
                    elinewidth=2.4, capsize=5)
        ax.annotate(f"{delta:+.1f}".replace("-", "−"), (delta, y), xytext=(0, 9),
                    textcoords="offset points", ha="center", color=color, weight="bold", fontsize=11,
                    bbox={"facecolor": PAPER, "edgecolor": "none", "pad": 0.4})
    rule(fig, 0.157)
    fig.text(0.04, 0.095, "Whiskers show simultaneous 95% intervals. Positive values favor waiting 25 turns.",
             fontsize=10.5, color=INK)
    fig.text(0.04, 0.042, "The mixed table includes one Adaptive, one Long-route player and one Hoarder.",
             fontsize=10, color=MUTED)
    save(fig, "wait-comparison.png")


def pilot_figure():
    with (SOURCE / "europe_pilot_results.csv").open(newline="") as f:
        rows = {(r["candidate"], r["opponents"]): r for r in csv.DictReader(f) if r["phase"] == "evaluation"}
    (n,) = {int(r["games"]) for r in rows.values()}
    names = {"finish": "Hoard and Finish", "fast": "Fast Builder", "regular": "Regular",
             "hoarder": "Hoarder", "adaptive": "Adaptive", "long": "Long-route player"}
    shades = ["#edf2f3", "#ccdde3", "#98bac9", "#426e83", "#204c68"]
    fig = figure("Six strategies at three tables", f"Pilot tournament   ·   {n} simulated games per matchup   ·   Four-player Europe", 6.4)
    ax = fig.add_axes([0.32, 0.17, 0.64, 0.61], facecolor=PAPER)
    ax.set(xlim=(0, 3), ylim=(6, 0))
    ax.axis("off")
    fig.text(0.04, 0.806, "Candidate", fontsize=11, color=MUTED, weight="bold")
    for j, (table, (opponents, _)) in enumerate(TABLES.items()):
        ax.text(j + 0.5, -0.25, TABLE_NAMES[table], ha="center", va="bottom",
                fontsize=11, weight="bold", color=INK)
        for i, (policy, label) in enumerate(names.items()):
            r = rows[policy, "/".join(opponents)]
            rate = float(r["win_pct"])
            shade = sum(rate >= threshold for threshold in (15, 30, 45, 60))
            color = "white" if shade >= 3 else INK
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=shades[shade], edgecolor=PAPER, lw=2))
            ax.text(j + 0.5, i + 0.40, f"{rate:g}%", ha="center", va="center",
                    fontsize=17, weight="bold", color=color)
            ax.text(j + 0.5, i + 0.75, f"{float(r['low95']):.1f}–{float(r['high95']):.1f}%",
                    ha="center", va="center", fontsize=10, color=color)
            if j == 0:
                row_y = 0.78 - (i + 0.5) * 0.61 / 6
                fig.text(0.04, row_y, label, va="center", fontsize=13, color=INK)
    rule(fig, 0.14)
    fig.text(0.04, 0.089, "Each cell shows the outright win rate with its 95% Wilson interval below.",
             fontsize=10.5, color=INK)
    fig.text(0.04, 0.045, "Hoard and Finish waits 25 turns. Mixed opponents are Adaptive, Long-route player and Hoarder.",
             fontsize=10, color=MUTED)
    save(fig, "pilot-win-rates.png")


if __name__ == "__main__":
    FIGURES.mkdir(parents=True, exist_ok=True)
    wait_figure()
    pilot_figure()
