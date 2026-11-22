"""Pull the headline numbers out of the tables and write outputs/summary.md."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .metrics import smm_to_cpr


def _pooled_cpr(lm: pd.DataFrame, mask) -> tuple[float, int]:
    d = lm[mask]
    if len(d) == 0:
        return float("nan"), 0
    return smm_to_cpr(d["prepaid"].sum() / len(d)), len(d)


def split_in_money(lm: pd.DataFrame, col: str, order) -> pd.DataFrame:
    """CPR for borrowers 1+ pt in the money vs 1+ pt out of the money, per bucket."""
    rows = []
    has = lm["incentive"].notna()
    for k in order:
        m = has & (lm[col] == k)
        cin, nin = _pooled_cpr(lm, m & (lm["incentive"] >= 1.0))
        cout, nout = _pooled_cpr(lm, m & (lm["incentive"] <= -1.0))
        rows.append({"bucket": k, "cpr_in_money": cin, "n_in_money": nin,
                     "cpr_out_money": cout, "n_out_money": nout})
    return pd.DataFrame(rows)


def headline_numbers(lm: pd.DataFrame, vt: pd.DataFrame, li: pd.DataFrame) -> dict:
    out = {}
    out["n_loans"] = lm["loan_id"].nunique()
    out["n_loan_months"] = len(lm)
    out["first_period"] = str(lm["period"].min())
    out["last_period"] = str(lm["period"].max())

    rows = []
    for v, g in vt.groupby("vintage"):
        lmv = lm[lm["vintage"] == v]
        last12 = lmv[lmv["period"] > lmv["period"].max() - 12]
        peak = g.loc[g["cpr"].idxmax()]
        rows.append(
            {
                "vintage": v,
                "loans": lmv["loan_id"].nunique(),
                "avg_note_rate": round(lmv.groupby("loan_id")["orig_rate"].first().mean(), 2),
                "lifetime_cpr": smm_to_cpr(lmv["prepaid"].mean()),
                "last_12m_cpr": smm_to_cpr(last12["prepaid"].mean()),
                "peak_cpr": peak["cpr"],
                "peak_month": str(peak["period"]),
            }
        )
    out["by_vintage"] = pd.DataFrame(rows)

    has_inc = lm["incentive"].notna()
    out["cpr_in_money"], out["n_in_money"] = _pooled_cpr(lm, has_inc & (lm["incentive"] >= 1.0))
    out["cpr_at_money"], out["n_at_money"] = _pooled_cpr(lm, has_inc & (lm["incentive"].abs() < 0.25))
    out["cpr_out_money"], out["n_out_money"] = _pooled_cpr(lm, has_inc & (lm["incentive"] <= -1.0))

    if len(li):
        latest = li.iloc[-1]
        peak_li = li.loc[li["share_locked_in"].idxmax()]
        out["lock_in_latest"] = (str(latest["period"]), latest["share_locked_in"])
        out["lock_in_peak"] = (str(peak_li["period"]), peak_li["share_locked_in"])
    return out


def _p(x):
    return "n/a" if pd.isna(x) else f"{x:.1%}"


def write_summary(h: dict, out_dir: Path, synthetic: bool) -> Path:
    lines = []
    if synthetic:
        lines += [
            "> **FAKE DATA.** These numbers come from the synthetic data generator, only to test",
            "> that the code runs. Don't quote them. Rerun on the real Freddie Mac files.",
            "",
        ]
    lines += [
        "# Mortgage prepayment analysis: summary",
        "",
        f"- Loans analyzed: **{h['n_loans']:,}** ({h['n_loan_months']:,} loan-months)",
        f"- Months covered: **{h['first_period']} to {h['last_period']}**",
        "",
        "## Prepayment speed by loan year",
        "",
        "| Loan year | Loans | Avg note rate | Lifetime CPR | Last 12 months CPR | Peak CPR (month) |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in h["by_vintage"].iterrows():
        lines.append(
            f"| {r['vintage']} | {r['loans']:,} | {r['avg_note_rate']:.2f}% | {_p(r['lifetime_cpr'])} "
            f"| {_p(r['last_12m_cpr'])} | {_p(r['peak_cpr'])} ({r['peak_month']}) |"
        )
    lines += [
        "",
        "## Does the refi incentive matter?",
        "",
        "| Borrower position | CPR | Loan-months |",
        "|---|---|---|",
        f"| In the money (rate 1+ pt above market) | {_p(h['cpr_in_money'])} | {h['n_in_money']:,} |",
        f"| At the money (within 0.25 pt) | {_p(h['cpr_at_money'])} | {h['n_at_money']:,} |",
        f"| Out of the money (rate 1+ pt below market) | {_p(h['cpr_out_money'])} | {h['n_out_money']:,} |",
        "",
    ]
    if "lock_in_latest" in h:
        lines += [
            "## Rate lock-in",
            "",
            f"- Share of outstanding loans 1+ pt below market, latest month ({h['lock_in_latest'][0]}): "
            f"**{_p(h['lock_in_latest'][1])}**",
            f"- Peak: **{_p(h['lock_in_peak'][1])}** in {h['lock_in_peak'][0]}",
            "",
        ]
    if "rate_buckets" in h and len(h["rate_buckets"]):
        rb = h["rate_buckets"]
        lines += [
            "## Prepayment speed by loan rate (last 12 months)",
            "",
            f"Window: {rb['window'].iloc[0]}. Market 30-yr rate in the latest month: about {h['market_now']:.2f}%.",
            "",
            "| Loan rate bucket | CPR | Loan-months |",
            "|---|---|---|",
        ]
        for _, r in rb.iterrows():
            lines.append(f"| {r['rate_bucket']:.1f}% to {r['rate_bucket'] + 0.49:.2f}% | {_p(r['cpr'])} | {r['loans']:,} |")
        lines.append("")
    for key, title in [("by_size_in_money", "loan size"), ("by_credit_in_money", "credit score")]:
        if key in h:
            lines += [
                f"## Does the incentive effect change by {title}?",
                "",
                f"| {title.capitalize()} | CPR, 1+ pt in the money | CPR, 1+ pt out of the money |",
                "|---|---|---|",
            ]
            for _, r in h[key].iterrows():
                lines.append(f"| {r['bucket']} | {_p(r['cpr_in_money'])} ({r['n_in_money']:,}) "
                             f"| {_p(r['cpr_out_money'])} ({r['n_out_money']:,}) |")
            lines += ["", "Loan-months in parentheses.", ""]
    lines += [
        "## Method notes",
        "",
        "- CPR = 1 - (1 - SMM)^12, where SMM = full payoffs / loans outstanding that month.",
        "- Counts full payoffs only (zero balance code 01). Partial prepayments are not included.",
        "- Payoffs include refinances and home sales. The data doesn't split them.",
        "- Refi incentive = loan rate minus the Freddie Mac PMMS 30-year rate, lagged one month.",
        "- Loan rate buckets use the loan's note rate. MBS pool coupons run about 0.5 to 0.75 pt lower.",
        "- Source: Freddie Mac Single-Family Loan-Level Dataset (sample files) and PMMS via FRED.",
        "",
    ]
    path = out_dir / "summary.md"
    path.write_text("\n".join(lines))
    return path
