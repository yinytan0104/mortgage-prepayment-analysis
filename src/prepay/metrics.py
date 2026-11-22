"""Prepayment math.

Key terms
---------
SMM (single monthly mortality): share of loans still outstanding at the start
    of a month that pay off in full that month.
CPR (conditional prepayment rate): SMM turned into an annual rate,
    CPR = 1 - (1 - SMM) ** 12. This is the number MBS traders quote.
Refi incentive: the loan's note rate minus the current market mortgage rate.
    Positive = the borrower could refinance into a lower rate.
    Negative = the borrower is "locked in" to a rate below the market.

Notes on method (keep these in mind when presenting results)
--------------------------------------------------------------
* We count full payoffs only (zero balance code 01). Partial prepayments
  ("curtailments") are ignored, so CPRs here run slightly below official
  agency CPRs.
* Payoffs include both refinances and home sales (turnover). The data doesn't
  separate them. Turnover is why CPR never goes to zero, even deep out of the
  money.
* Both a count-based and a balance-weighted (UPB) CPR are produced. Freddie
  masks the current UPB in the first months of a loan's life in some
  releases, so we fall back to the original balance when it is reported as 0.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .load import PREPAY_CODE


def smm_to_cpr(smm):
    return 1 - (1 - smm) ** 12


def build_loan_months(orig: pd.DataFrame, perf: pd.DataFrame) -> pd.DataFrame:
    """One row per loan per month the loan was outstanding at the start of the month."""
    lm = perf.merge(
        orig[[c for c in ["loan_id", "vintage", "orig_rate", "orig_upb", "credit_score", "orig_ltv", "orig_dti"]
              if c in orig.columns]],
        on="loan_id",
        how="inner",
    )
    lm = lm.sort_values(["loan_id", "period"]).reset_index(drop=True)

    # Balance at start of month = last month's reported balance (or original balance)
    upb = lm["current_upb"].where(lm["current_upb"] > 0)
    upb_start = upb.groupby(lm["loan_id"]).shift(1)
    lm["upb_start"] = upb_start.fillna(lm["orig_upb"])
    # If masked balances left gaps, carry the last known balance forward
    lm["upb_start"] = lm.groupby("loan_id")["upb_start"].ffill()

    lm["note_rate"] = lm["current_rate"].fillna(lm["orig_rate"])
    lm["prepaid"] = (lm["zero_balance_code"] == PREPAY_CODE).astype(int)
    lm["prepaid_upb"] = lm["prepaid"] * lm["upb_start"]
    return lm


def add_incentive(lm: pd.DataFrame, market: pd.Series, lag_months: int = 1) -> pd.DataFrame:
    """Attach the market rate and the refi incentive.

    lag_months=1 uses last month's market rate, since a refinance started when
    rates drop usually closes a month or two later.
    """
    m = market.copy()
    m.index = m.index + lag_months
    out = lm.merge(m.rename("market_rate"), left_on="period", right_index=True, how="left")
    out["incentive"] = out["note_rate"] - out["market_rate"]
    return out


def cpr_by(lm: pd.DataFrame, keys) -> pd.DataFrame:
    keys = [keys] if isinstance(keys, str) else list(keys)
    g = lm.groupby(keys, observed=True)
    out = pd.DataFrame(
        {
            "loans": g["prepaid"].size(),
            "payoffs": g["prepaid"].sum(),
            "upb_start": g["upb_start"].sum(),
            "prepaid_upb": g["prepaid_upb"].sum(),
        }
    )
    out["cpr"] = smm_to_cpr(out["payoffs"] / out["loans"])
    out["cpr_upb"] = smm_to_cpr(out["prepaid_upb"] / out["upb_start"])
    return out.drop(columns=["upb_start", "prepaid_upb"]).reset_index()


def monthly_cpr_by_vintage(lm: pd.DataFrame, min_loans: int = 200) -> pd.DataFrame:
    t = cpr_by(lm, ["vintage", "period"])
    return t[t["loans"] >= min_loans]


def s_curve(lm: pd.DataFrame, bin_width: float = 0.25, lo: float = -4.0, hi: float = 3.0,
            min_loans: int = 500, by_vintage: bool = False) -> pd.DataFrame:
    """CPR by refi-incentive bucket. The classic 'S-curve' of prepayments."""
    d = lm.dropna(subset=["incentive"]).copy()
    x = d["incentive"].clip(lo, hi - 1e-9)
    d["incentive_mid"] = (np.floor((x - lo) / bin_width) * bin_width + lo + bin_width / 2).round(3)
    keys = ["vintage", "incentive_mid"] if by_vintage else ["incentive_mid"]
    t = cpr_by(d, keys)
    return t[t["loans"] >= min_loans]


def cpr_by_loan_age(lm: pd.DataFrame, max_age: int = 72, min_loans: int = 500) -> pd.DataFrame:
    """Seasoning: brand new loans prepay slowly, then speeds ramp up."""
    t = cpr_by(lm[lm["loan_age"] <= max_age], "loan_age")
    return t[t["loans"] >= min_loans]


def lock_in_share(lm: pd.DataFrame, threshold: float = -1.0) -> pd.DataFrame:
    """Share of outstanding loans whose rate is at least |threshold| points below market."""
    d = lm.dropna(subset=["incentive"])
    g = d.groupby("period")
    out = pd.DataFrame(
        {
            "loans": g.size(),
            "share_locked_in": g["incentive"].apply(lambda s: (s <= threshold).mean()),
            "avg_note_rate": g["note_rate"].mean(),
            "market_rate": g["market_rate"].mean(),
        }
    )
    return out.reset_index()


# ---------------------------------------------------------------------------
# Borrower and loan buckets
# ---------------------------------------------------------------------------

SIZE_LABELS = ["Under $200K", "$200K to $400K", "$400K+"]
CREDIT_LABELS = ["Under 700", "700 to 759", "760+"]


def add_buckets(lm: pd.DataFrame) -> pd.DataFrame:
    """Add loan-rate ('coupon'), loan-size and credit-score buckets.

    Rate buckets are half a point wide and named by their lower edge, so
    "6.5%" means loans with a rate from 6.50% to 6.99%. Note: an MBS coupon is
    usually about 0.5 to 0.75 pt below the loans' note rate (servicing and
    guarantee fees come out first), so these are loan-rate buckets, not
    exact pool coupons.
    """
    out = lm.copy()
    out["rate_bucket"] = np.floor(out["note_rate"] * 2) / 2
    out["size_bucket"] = pd.cut(out["orig_upb"], [0, 200_000, 400_000, np.inf],
                                labels=SIZE_LABELS, right=False)
    out["credit_bucket"] = pd.cut(out["credit_score"], [0, 700, 760, 1000],
                                  labels=CREDIT_LABELS, right=False)
    return out


def cpr_by_rate_bucket(lm: pd.DataFrame, last_n_months: int = 12, min_loans: int = 2000) -> pd.DataFrame:
    """CPR by loan-rate bucket over the most recent months. The trader's view."""
    end = lm["period"].max()
    recent = lm[lm["period"] > end - last_n_months]
    t = cpr_by(recent, "rate_bucket")
    t = t[t["loans"] >= min_loans].copy()
    t["window"] = f"{end - last_n_months + 1} to {end}"
    return t


def s_curve_by(lm: pd.DataFrame, col: str, bin_width: float = 0.5, lo: float = -3.0, hi: float = 3.0,
               min_loans: int = 1000) -> pd.DataFrame:
    """S-curve split by another column, e.g. size_bucket or credit_bucket."""
    d = lm.dropna(subset=["incentive", col]).copy()
    x = d["incentive"].clip(lo, hi - 1e-9)
    d["incentive_mid"] = (np.floor((x - lo) / bin_width) * bin_width + lo + bin_width / 2).round(3)
    t = cpr_by(d, [col, "incentive_mid"])
    return t[t["loans"] >= min_loans]
