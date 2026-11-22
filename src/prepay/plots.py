"""Charts. Each function saves one PNG and returns its path."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

COLORS = ["#1d3b5c", "#d1863a", "#3a8f6b", "#8a4fa3", "#c0392b", "#5d6d7e"]

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "font.size": 10,
    }
)


def _pct(ax):
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))


def _save(fig, out_dir: Path, name: str, note: str | None) -> Path:
    if note:
        fig.text(0.01, 0.01, note, fontsize=7.5, color="#777")
    fig.tight_layout(rect=(0, 0.03 if note else 0, 1, 1))
    path = out_dir / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_cpr_over_time(vt: pd.DataFrame, market: pd.Series, out_dir: Path, note=None) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for i, (v, g) in enumerate(vt.groupby("vintage")):
        ax.plot(g["period"].dt.to_timestamp(), g["cpr"], label=f"{v} loans",
                color=COLORS[i % len(COLORS)], lw=1.8)
    _pct(ax)
    ax.set_ylabel("Prepayment speed (CPR)")
    ax.set_title("Prepayment speed by loan year")
    ax2 = ax.twinx()
    lo, hi = vt["period"].min(), vt["period"].max()
    m = market[(market.index >= lo) & (market.index <= hi)]
    ax2.plot(m.index.to_timestamp(), m.values, color="#999", ls="--", lw=1.2,
             label="30-yr mortgage rate")
    ax2.set_ylabel("Market rate (%)", color="#777")
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)
    return _save(fig, out_dir, "01_cpr_over_time.png", note)


def plot_s_curve(sc: pd.DataFrame, out_dir: Path, note=None) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(sc["incentive_mid"], sc["cpr"], marker="o", ms=4, color=COLORS[0], lw=2)
    ax.axvline(0, color="#999", lw=1, ls=":")
    ax.text(0.05, ax.get_ylim()[1] * 0.92, "rates below my loan  →", fontsize=8.5, color="#555")
    ax.text(-0.05, ax.get_ylim()[1] * 0.92, "←  rates above my loan", fontsize=8.5,
            color="#555", ha="right")
    _pct(ax)
    ax.set_xlabel("Refi incentive (loan rate minus market rate, % points)")
    ax.set_ylabel("Prepayment speed (CPR)")
    ax.set_title("The prepayment S-curve")
    return _save(fig, out_dir, "02_s_curve.png", note)


def plot_s_curve_by_vintage(scv: pd.DataFrame, out_dir: Path, note=None) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for i, (v, g) in enumerate(scv.groupby("vintage")):
        ax.plot(g["incentive_mid"], g["cpr"], marker="o", ms=3, lw=1.6,
                color=COLORS[i % len(COLORS)], label=f"{v} loans")
    ax.axvline(0, color="#999", lw=1, ls=":")
    _pct(ax)
    ax.set_xlabel("Refi incentive (% points)")
    ax.set_ylabel("Prepayment speed (CPR)")
    ax.set_title("S-curve by loan year")
    ax.legend(frameon=False)
    return _save(fig, out_dir, "03_s_curve_by_vintage.png", note)


def plot_lock_in(li: pd.DataFrame, out_dir: Path, threshold: float, note=None) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    t = li["period"].dt.to_timestamp()
    ax.fill_between(t, li["share_locked_in"], color=COLORS[1], alpha=0.35)
    ax.plot(t, li["share_locked_in"], color=COLORS[1], lw=1.8)
    _pct(ax)
    ax.set_ylabel(f"Loans {abs(threshold):g}+ pts below market")
    ax.set_title("Rate lock-in: share of borrowers with a rate well below today's")
    return _save(fig, out_dir, "04_lock_in.png", note)


def plot_seasoning(sa: pd.DataFrame, out_dir: Path, note=None) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(sa["loan_age"], sa["cpr"], color=COLORS[2], lw=2)
    _pct(ax)
    ax.set_xlabel("Loan age (months)")
    ax.set_ylabel("Prepayment speed (CPR)")
    ax.set_title("Seasoning: speeds by loan age")
    return _save(fig, out_dir, "05_seasoning.png", note)
